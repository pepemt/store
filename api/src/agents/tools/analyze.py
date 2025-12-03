"""
Contextual analysis tools for images and product comparison.

This module provides:
- ContextualAnalyzer: Analyzes images based on what the orchestrator needs
- ProductComparator: Compares N products on M criteria
"""

import logging
import json
import re
import os
import sys
import asyncio
from typing import Optional, List, Dict, Any, Tuple

import oci
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import (
    ChatDetails,
    OnDemandServingMode,
    GenericChatRequest,
    UserMessage,
    SystemMessage,
    TextContent,
    ImageContent,
    ImageUrl,
)

# Add parent directory (agents) to path for imports
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

from state import (
    ImageData,
    ImageAnalysis,
    ComparisonResult,
    ProductDict,
)
from llm_config import llm

logger = logging.getLogger(__name__)


# OCI Vision client singleton
_oci_vision_client = None


def _get_oci_vision_client():
    """Get or create OCI GenerativeAI client for vision."""
    global _oci_vision_client
    if _oci_vision_client is None:
        try:
            config = oci.config.from_file(profile_name="DEFAULT")
            service_endpoint = os.getenv("OCI_GENAI_ENDPOINT")
            _oci_vision_client = GenerativeAiInferenceClient(
                config=config,
                service_endpoint=service_endpoint
            )
            logger.info(f"OCI Vision client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OCI Vision client: {e}")
            raise
    return _oci_vision_client


class ContextualAnalyzer:
    """
    Contextual image analyzer.

    NOT a generic "describe the image" tool.
    The orchestrator specifies WHAT to extract based on the user's intent.

    Examples:
    - context="User wants similar products" → Extract: type, color, style, pattern
    - context="User wants outfit suggestions" → Extract: all items, suggest combinations
    - context="User wants to compare products" → Extract: attributes for comparison matrix
    """

    # Prompts for different analysis types
    ANALYSIS_PROMPTS = {
        "attributes": """Analyze this image for product search.

Extract and return as JSON:
{{
    "type": "clothing type (specific, e.g., 'casual t-shirt', not just 'shirt')",
    "colors": ["primary color", "secondary colors if any"],
    "pattern": "pattern type (solid, stripes, floral, character print, etc.)",
    "style": "style category (casual, formal, sporty, elegant)",
    "material": "visible material or 'unknown'",
    "gender_target": "men/women/unisex/boys/girls or 'unknown'",
    "distinctive_features": ["list of unique features like 'unicorn design', 'rainbow pattern'"],
    "search_queries": ["2-3 search queries to find similar products"]
}}

Focus on attributes useful for finding similar products.
{context}""",

        "items": """Identify ALL distinct items in this image.

Return as JSON:
{{
    "items": [
        {{
            "id": "item_1",
            "type": "item type",
            "attributes": {{
                "color": "color",
                "style": "style"
            }},
            "position": "description of position in image"
        }}
    ],
    "total_count": number,
    "categories_found": ["list of categories present"]
}}

{context}""",

        "outfit": """Analyze this outfit/wardrobe image CAREFULLY and generate SPECIFIC search queries BY COMPONENT TYPE.

IMPORTANT: Look at the image carefully and identify the EXACT type of each garment:
- SKIRT vs SHORTS: A skirt is a single piece that flows, shorts have two leg openings
- COAT/BLAZER vs SHIRT: A coat/blazer is worn over other clothes, usually longer
- BLOUSE vs T-SHIRT: A blouse is more formal, often with buttons and collar
- DRESS vs SKIRT+TOP: A dress is one piece covering torso and legs

Return as JSON:
{{
    "current_items": [
        {{
            "type": "EXACT item type - be SPECIFIC (e.g., 'long coat', 'pleated skirt', 'silk blouse', 'ankle boots')",
            "component": "top/bottom/outerwear/shoes/accessories",
            "color": "specific color (e.g., 'tan', 'navy blue', 'burgundy')",
            "style": "style (formal, casual, elegant, sporty)",
            "material": "material if visible (leather, silk, wool, denim)",
            "gender": "women/men/unisex/boys/girls"
        }}
    ],
    "outfit_analysis": {{
        "overall_style": "detailed style description",
        "color_palette": ["list all colors"],
        "occasion_suitable": ["office", "party", "casual", "formal"],
        "gender_detected": "women/men/unisex"
    }},
    "component_queries": {{
        "outerwear": ["ENGLISH query for coats/jackets/blazers if present"],
        "top": ["ENGLISH query for shirts/blouses/sweaters"],
        "bottom": ["ENGLISH query for skirts/pants/trousers - NOT shorts if it's clearly a skirt"],
        "shoes": ["ENGLISH query for footwear"],
        "accessories": ["ENGLISH query for bags/jewelry/scarves if present"]
    }},
    "search_queries": [
        "fallback ENGLISH search query 1",
        "fallback ENGLISH search query 2"
    ]
}}

CRITICAL RULES:
1. BE PRECISE with garment types - "skirt" NOT "shorts", "coat" NOT "shirt", "blouse" NOT "t-shirt"
2. Include component "outerwear" for coats, blazers, jackets worn over other clothes
3. All queries must be in ENGLISH with gender (women/men)
4. Include color, material, and style in queries (e.g., "tan wool coat women formal")
5. Make queries SPECIFIC enough to find similar items

Example for formal women's outfit with coat, blouse, skirt, heels, handbag:
{{
    "component_queries": {{
        "outerwear": ["tan long wool coat women formal elegant"],
        "top": ["black silk blouse women formal collar"],
        "bottom": ["gray pleated midi skirt women formal"],
        "shoes": ["black leather heels women formal"],
        "accessories": ["black leather handbag women elegant"]
    }}
}}

{context}""",

        "comparison": """Extract product attributes for comparison.

Return as JSON:
{{
    "product_name": "identified product name",
    "category": "product category",
    "attributes": {{
        "color": "color",
        "style": "style",
        "material": "material if visible",
        "features": ["list of features"]
    }},
    "price_tier": "budget/mid-range/premium (estimate from appearance)",
    "suitable_for": ["occasions/uses"]
}}

{context}""",

        "auto": """Analyze this image based on the context provided.

{context}

Return your analysis as structured JSON with relevant fields for the context."""
    }

    async def analyze(
        self,
        images: List[ImageData],
        analysis_context: str,
        extraction_type: str = "auto"
    ) -> List[ImageAnalysis]:
        """
        Perform contextual analysis on images.

        Args:
            images: List of images to analyze
            analysis_context: What the orchestrator wants to know
            extraction_type: Type of extraction (attributes, items, outfit, comparison, auto)

        Returns:
            List of ImageAnalysis results
        """
        analyses = []

        for image in images:
            try:
                result = await self._analyze_single_image(
                    image,
                    analysis_context,
                    extraction_type
                )
                analyses.append(result)
            except Exception as e:
                logger.error(f"Error analyzing image {image.get('id', 'unknown')}: {e}")
                # Return error result
                analyses.append(ImageAnalysis(
                    image_id=image.get("id", "unknown"),
                    analysis_type=extraction_type,
                    extracted_items=[],
                    attributes={"error": str(e)},
                    search_queries=[]
                ))

        return analyses

    async def _analyze_single_image(
        self,
        image: ImageData,
        analysis_context: str,
        extraction_type: str
    ) -> ImageAnalysis:
        """Analyze a single image."""
        # Build prompt based on extraction type
        prompt_template = self.ANALYSIS_PROMPTS.get(
            extraction_type,
            self.ANALYSIS_PROMPTS["auto"]
        )
        prompt = prompt_template.format(context=f"Context: {analysis_context}")

        # Call vision model
        response_text = await self._call_vision_model(
            image["data"],
            image.get("mime_type", "image/jpeg"),
            prompt
        )

        # Parse JSON response
        result = self._parse_json_response(response_text)
        logger.info(f"Parsed result keys: {list(result.keys()) if isinstance(result, dict) else 'NOT A DICT'}")
        logger.info(f"search_queries in result: {result.get('search_queries', 'NOT FOUND')}")

        # Build ImageAnalysis based on extraction type
        if extraction_type == "attributes":
            return ImageAnalysis(
                image_id=image.get("id", "unknown"),
                analysis_type=extraction_type,
                extracted_items=[{
                    "type": result.get("type", "unknown"),
                    "colors": result.get("colors", []),
                    "pattern": result.get("pattern", "unknown"),
                    "style": result.get("style", "unknown"),
                }],
                attributes=result,
                search_queries=result.get("search_queries", [])
            )
        elif extraction_type == "items":
            return ImageAnalysis(
                image_id=image.get("id", "unknown"),
                analysis_type=extraction_type,
                extracted_items=result.get("items", []),
                attributes={
                    "total_count": result.get("total_count", 0),
                    "categories_found": result.get("categories_found", [])
                },
                search_queries=[]
            )
        elif extraction_type == "outfit":
            # Get search queries directly from result (now in English)
            search_queries = result.get("search_queries", [])

            # Get component queries (structured by type: top, bottom, shoes, accessories)
            component_queries = result.get("component_queries", {})

            # If component_queries is empty, try to generate from current_items
            if not component_queries and result.get("current_items"):
                component_queries = self._generate_component_queries_from_items(
                    result.get("current_items", []),
                    result.get("outfit_analysis", {})
                )
                logger.info(f"Generated component_queries from items: {list(component_queries.keys())}")

            logger.info(f"component_queries keys: {list(component_queries.keys()) if component_queries else 'EMPTY'}")

            analysis_result = ImageAnalysis(
                image_id=image.get("id", "unknown"),
                analysis_type=extraction_type,
                extracted_items=result.get("current_items", []),
                attributes=result.get("outfit_analysis", {}),
                search_queries=search_queries,
                outfit_suggestions=result.get("outfit_suggestions", []),
                component_queries=component_queries
            )
            return analysis_result
        else:
            # Auto or comparison
            return ImageAnalysis(
                image_id=image.get("id", "unknown"),
                analysis_type=extraction_type,
                extracted_items=[result] if isinstance(result, dict) else [],
                attributes=result if isinstance(result, dict) else {},
                search_queries=result.get("search_queries", []) if isinstance(result, dict) else []
            )

    async def _call_vision_model(
        self,
        image_data: str,
        mime_type: str,
        prompt: str
    ) -> str:
        """Call the OCI Vision model."""
        try:
            logger.info(f"=== VISION MODEL DEBUG ===")
            logger.info(f"Image data length: {len(image_data)} chars")
            logger.info(f"MIME type: {mime_type}")
            logger.info(f"Prompt (first 200 chars): {prompt[:200]}...")

            client = _get_oci_vision_client()

            image_url = f"data:{mime_type};base64,{image_data}"
            logger.info(f"Image URL prefix: {image_url[:80]}...")

            system_msg = SystemMessage(
                content=[TextContent(
                    text="You are a fashion product analyst. Analyze images and return structured JSON responses. Always be accurate and detailed."
                )]
            )

            user_content = [
                ImageContent(image_url=ImageUrl(url=image_url)),
                TextContent(text=prompt)
            ]
            user_msg = UserMessage(content=user_content)

            chat_request = GenericChatRequest(
                messages=[system_msg, user_msg],
                max_tokens=1000,
                temperature=0.3,
                top_p=0.9,
                is_stream=False
            )

            chat_details = ChatDetails(
                compartment_id=os.getenv("OCI_GENAI_COMPARTMENT_ID"),
                serving_mode=OnDemandServingMode(
                    model_id=os.getenv("OCI_GENAI_VISION_MODEL_ID", "meta.llama-3.2-90b-vision-instruct")
                ),
                chat_request=chat_request
            )

            logger.info(f"Calling OCI Vision API...")
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat(chat_details)
            )
            logger.info(f"OCI Vision API response received")

            # Extract response content
            logger.info(f"Response has data: {response.data is not None}")
            if response.data and response.data.chat_response:
                chat_response = response.data.chat_response
                logger.info(f"Chat response has choices: {hasattr(chat_response, 'choices') and bool(chat_response.choices)}")
                if hasattr(chat_response, 'choices') and chat_response.choices:
                    logger.info(f"Number of choices: {len(chat_response.choices)}")
                    first_choice = chat_response.choices[0]
                    if hasattr(first_choice, 'message') and first_choice.message:
                        content = first_choice.message.content
                        logger.info(f"Content type: {type(content).__name__}")
                        if isinstance(content, list):
                            result = " ".join(
                                c.text if hasattr(c, 'text') else str(c)
                                for c in content
                            )
                            logger.info(f"Vision result (first 500 chars): {result[:500]}")
                            return result
                        logger.info(f"Vision result (first 500 chars): {str(content)[:500]}")
                        return str(content)

            logger.warning("Vision model returned empty or invalid response structure")
            # Return fallback with search_queries to prevent cascade failure
            return json.dumps({
                "error": "Empty response from vision model",
                "search_queries": ["clothing fashion style"],
                "type": "unknown",
                "colors": [],
                "style": "casual",
                "parse_error": True
            })

        except Exception as e:
            logger.error(f"Vision model call failed: {e}", exc_info=True)
            # Return fallback with search_queries to prevent cascade failure
            return json.dumps({
                "error": str(e),
                "search_queries": ["clothing fashion"],
                "type": "unknown",
                "colors": [],
                "style": "casual",
                "parse_error": True
            })

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from model response. Always ensures search_queries exists."""
        # Try to find JSON in the response
        try:
            # First, try direct parse
            result = json.loads(response_text)
            return self._ensure_search_queries(result)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                return self._ensure_search_queries(result)
            except json.JSONDecodeError:
                pass

        # Try to find any JSON object (handle nested braces)
        json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', response_text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return self._ensure_search_queries(result)
            except json.JSONDecodeError:
                pass

        # Parse text response to extract items (vision model sometimes returns markdown)
        logger.info("JSON parsing failed, attempting to extract items from text response")
        extracted_result = self._parse_text_response_to_items(response_text)
        if extracted_result:
            logger.info(f"Extracted {len(extracted_result.get('current_items', []))} items from text")
            return extracted_result

        # Return response as text description with FALLBACK search_queries
        return {
            "description": response_text,
            "parse_error": True,
            "search_queries": ["clothing fashion"],  # CRITICAL: Always include
            "type": "unknown",
            "colors": [],
            "style": "casual"
        }

    def _parse_text_response_to_items(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse markdown/text response from vision model to extract clothing items."""
        # Common item patterns in markdown lists
        # "A long, tan coat with a lapel collar"
        # "A black shirt with a collar"
        # "A pair of gray shorts with a floral pattern"

        items = []
        component_queries: Dict[str, List[str]] = {}

        # Component type keywords
        TOP_KEYWORDS = ["coat", "shirt", "blouse", "sweater", "hoodie", "jacket", "top", "vest", "cardigan", "t-shirt", "polo"]
        BOTTOM_KEYWORDS = ["pants", "jeans", "trousers", "shorts", "skirt", "leggings"]
        SHOES_KEYWORDS = ["shoes", "sneakers", "boots", "sandals", "heels", "loafers", "flats"]
        ACCESSORIES_KEYWORDS = ["bag", "handbag", "hat", "belt", "scarf", "watch", "glasses", "socks", "jewelry"]

        # Color keywords
        COLORS = ["black", "white", "blue", "red", "pink", "green", "grey", "gray", "brown",
                  "yellow", "orange", "purple", "beige", "navy", "tan", "gold", "silver", "cream"]

        # Find items in bullet points or numbered lists
        lines = text.split("\n")
        for line in lines:
            line_lower = line.lower().strip()

            # Skip non-item lines
            if not line_lower or line_lower.startswith("**") and line_lower.endswith("**"):
                continue

            # Extract item from list markers
            item_text = re.sub(r'^[\*\-\d\.]+\s*', '', line.strip())
            if not item_text or len(item_text) < 5:
                continue

            item_lower = item_text.lower()

            # Detect component type
            component = None
            item_type = "unknown"

            for kw in TOP_KEYWORDS:
                if kw in item_lower:
                    component = "top"
                    item_type = kw
                    break
            if not component:
                for kw in BOTTOM_KEYWORDS:
                    if kw in item_lower:
                        component = "bottom"
                        item_type = kw
                        break
            if not component:
                for kw in SHOES_KEYWORDS:
                    if kw in item_lower:
                        component = "shoes"
                        item_type = kw
                        break
            if not component:
                for kw in ACCESSORIES_KEYWORDS:
                    if kw in item_lower:
                        component = "accessories"
                        item_type = kw
                        break

            if not component:
                continue

            # Extract color
            color = None
            for c in COLORS:
                if c in item_lower:
                    color = c
                    break

            # Build item dict
            item = {
                "type": item_type,
                "component": component,
                "color": color or "unknown",
                "style": "casual",
                "description": item_text
            }
            items.append(item)

            # Build search query for component
            query_parts = [item_type]
            if color:
                query_parts.append(color)
            query_parts.append("clothing")  # Generic term to help search

            query = " ".join(query_parts)
            if component not in component_queries:
                component_queries[component] = []
            component_queries[component].append(query)

        if not items:
            return None

        # Build fallback search_queries from first items of each component
        search_queries = []
        for comp in ["top", "bottom", "shoes", "accessories"]:
            if comp in component_queries and component_queries[comp]:
                search_queries.append(component_queries[comp][0])

        if not search_queries:
            search_queries = ["clothing fashion"]

        return {
            "current_items": items,
            "outfit_analysis": {
                "overall_style": "casual",
                "color_palette": list(set(item.get("color") for item in items if item.get("color") != "unknown")),
                "gender_detected": "unisex"
            },
            "search_queries": search_queries,
            "component_queries": component_queries,
            "parsed_from_text": True
        }

    def _ensure_search_queries(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure search_queries exists in result, generate from attributes if missing."""
        if not isinstance(result, dict):
            return {
                "original": result,
                "search_queries": ["clothing fashion"],
                "parse_error": True
            }

        if "search_queries" not in result or not result["search_queries"]:
            result["search_queries"] = self._generate_fallback_queries(result)
            logger.info(f"Generated fallback search_queries: {result['search_queries']}")

        return result

    def _generate_fallback_queries(self, result: Dict[str, Any]) -> List[str]:
        """Generate search queries from available attributes."""
        parts = []

        # Extract available attributes
        item_type = result.get("type", "")
        if not item_type and result.get("current_items"):
            # For outfit analysis, get type from first item
            first_item = result["current_items"][0] if result["current_items"] else {}
            item_type = first_item.get("type", "")

        if item_type and item_type != "unknown":
            parts.append(item_type)

        colors = result.get("colors", [])
        if not colors and result.get("outfit_analysis"):
            colors = result["outfit_analysis"].get("color_palette", [])
        if colors:
            parts.append(colors[0] if isinstance(colors, list) else str(colors))

        style = result.get("style", "")
        if not style and result.get("outfit_analysis"):
            style = result["outfit_analysis"].get("overall_style", "")
        if style:
            parts.append(style)

        gender = result.get("gender_target", "")
        if not gender and result.get("outfit_analysis"):
            gender = result["outfit_analysis"].get("gender_detected", "")
        if gender:
            parts.append(gender)

        if parts:
            return [" ".join(parts)]
        else:
            return ["clothing fashion style"]

    def _generate_component_queries_from_items(
        self,
        items: List[Dict[str, Any]],
        outfit_analysis: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate component_queries from current_items when vision model doesn't provide them."""
        # Component type mapping
        COMPONENT_MAPPING = {
            # Tops
            "shirt": "top", "t-shirt": "top", "blouse": "top", "sweater": "top",
            "hoodie": "top", "jacket": "top", "coat": "top", "cardigan": "top",
            "top": "top", "vest": "top", "tank": "top", "polo": "top",
            # Bottoms
            "pants": "bottom", "jeans": "bottom", "trousers": "bottom", "shorts": "bottom",
            "skirt": "bottom", "leggings": "bottom", "bottom": "bottom",
            # Shoes
            "shoes": "shoes", "sneakers": "shoes", "boots": "shoes", "sandals": "shoes",
            "heels": "shoes", "loafers": "shoes", "flats": "shoes", "footwear": "shoes",
            # Accessories
            "bag": "accessories", "handbag": "accessories", "hat": "accessories",
            "belt": "accessories", "scarf": "accessories", "jewelry": "accessories",
            "watch": "accessories", "glasses": "accessories", "accessories": "accessories",
            "socks": "accessories",
        }

        component_queries: Dict[str, List[str]] = {}
        gender = outfit_analysis.get("gender_detected", "")

        for item in items:
            item_type = item.get("type", "").lower()
            component = item.get("component", "").lower()

            # Determine component category
            if component and component in ["top", "bottom", "shoes", "accessories"]:
                category = component
            else:
                # Infer from type
                category = None
                for keyword, cat in COMPONENT_MAPPING.items():
                    if keyword in item_type:
                        category = cat
                        break
                if not category:
                    continue  # Skip unknown items

            # Build query for this item
            query_parts = []

            # Type
            if item.get("type"):
                query_parts.append(item["type"])

            # Color
            if item.get("color"):
                query_parts.append(item["color"])

            # Style
            if item.get("style"):
                query_parts.append(item["style"])

            # Gender (from item or outfit analysis)
            item_gender = item.get("gender", gender)
            if item_gender:
                query_parts.append(item_gender)

            if query_parts:
                query = " ".join(query_parts)
                if category not in component_queries:
                    component_queries[category] = []
                component_queries[category].append(query)

        return component_queries


class ProductComparator:
    """
    Generic product comparator for N products on M criteria.

    Supports comparing any number of products (not limited to 2).
    """

    DEFAULT_CRITERIA = ["price", "category", "color", "style"]

    async def compare(
        self,
        products: List[ProductDict],
        criteria: Optional[List[str]] = None,
        user_priorities: Optional[List[str]] = None
    ) -> ComparisonResult:
        """
        Compare N products on M criteria.

        Args:
            products: List of products to compare (2, 3, 4, N...)
            criteria: Criteria to compare (auto-detected if None)
            user_priorities: What matters most to the user

        Returns:
            ComparisonResult with matrix and insights
        """
        if not products:
            return ComparisonResult(
                products=[],
                criteria=[],
                matrix={},
                insights={"error": "No products to compare"},
                markdown_table=""
            )

        # Auto-detect criteria if not provided
        if not criteria:
            criteria = self._auto_detect_criteria(products)

        # Build comparison matrix
        matrix = self._build_comparison_matrix(products, criteria)

        # Generate insights using LLM
        insights = await self._generate_insights(products, matrix, criteria, user_priorities)

        # Generate markdown table
        markdown_table = self._generate_markdown_table(products, matrix, criteria)

        return ComparisonResult(
            products=products,
            criteria=criteria,
            matrix=matrix,
            insights=insights,
            markdown_table=markdown_table,
            recommendation=insights.get("recommendation")
        )

    def _auto_detect_criteria(self, products: List[ProductDict]) -> List[str]:
        """Auto-detect relevant comparison criteria based on available data."""
        criteria = []

        # Check what fields are available
        sample = products[0] if products else {}

        if "price" in sample:
            criteria.append("price")
        if sample.get("category") or sample.get("product_type"):
            criteria.append("category")
        if sample.get("color") or sample.get("color_group"):
            criteria.append("color")
        if sample.get("department"):
            criteria.append("department")
        if sample.get("product_group"):
            criteria.append("product_group")
        if sample.get("rating"):
            criteria.append("rating")
        if sample.get("description"):
            criteria.append("description")

        return criteria or self.DEFAULT_CRITERIA

    def _build_comparison_matrix(
        self,
        products: List[ProductDict],
        criteria: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Build comparison matrix [criterion][product_id]."""
        matrix = {}

        for criterion in criteria:
            matrix[criterion] = {}
            for product in products:
                pid = str(product.get("id", "unknown"))
                value = self._extract_criterion_value(product, criterion)
                matrix[criterion][pid] = value

        return matrix

    def _extract_criterion_value(self, product: ProductDict, criterion: str) -> Any:
        """Extract value for a criterion from a product."""
        if criterion == "price":
            return product.get("price", "N/A")
        elif criterion == "category":
            return product.get("category") or product.get("product_type") or "N/A"
        elif criterion == "color":
            return product.get("color") or product.get("color_group") or "N/A"
        elif criterion == "department":
            return product.get("department") or "N/A"
        elif criterion == "product_group":
            return product.get("product_group") or "N/A"
        elif criterion == "rating":
            return product.get("rating") or "N/A"
        elif criterion == "description":
            desc = product.get("description") or ""
            return desc[:100] + "..." if len(desc) > 100 else desc or "N/A"
        else:
            return product.get(criterion, "N/A")

    async def _generate_insights(
        self,
        products: List[ProductDict],
        matrix: Dict[str, Dict[str, Any]],
        criteria: List[str],
        user_priorities: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Generate comparison insights using LLM."""
        try:
            # Build comparison summary for LLM
            product_summaries = []
            for i, p in enumerate(products, 1):
                summary = f"Product {i}: {p.get('name', 'Unknown')} - ${p.get('price', 'N/A')}"
                if p.get('color'):
                    summary += f", {p.get('color')}"
                if p.get('category'):
                    summary += f", {p.get('category')}"
                product_summaries.append(summary)

            prompt = f"""Compare these products and provide insights:

{chr(10).join(product_summaries)}

Comparison criteria: {', '.join(criteria)}
"""
            if user_priorities:
                prompt += f"User priorities: {', '.join(user_priorities)}\n"

            prompt += """
Provide a brief analysis in JSON format:
{
    "best_value": "product number with best price/quality ratio",
    "highest_quality": "product number that seems highest quality",
    "recommendation": "brief recommendation based on the comparison",
    "pros_cons": {
        "product_1": {"pros": ["..."], "cons": ["..."]},
        ...
    }
}
"""

            response = await llm.ainvoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Try to parse JSON
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except:
                        pass
                return {"analysis": response_text}

        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {"error": str(e)}

    def _generate_markdown_table(
        self,
        products: List[ProductDict],
        matrix: Dict[str, Dict[str, Any]],
        criteria: List[str]
    ) -> str:
        """Generate markdown comparison table."""
        if not products:
            return ""

        # Header row
        headers = ["Criterio"] + [p.get("name", f"Producto {i}")[:20] for i, p in enumerate(products, 1)]
        header_line = "| " + " | ".join(headers) + " |"
        separator = "|" + "|".join(["---"] * len(headers)) + "|"

        # Data rows
        rows = []
        for criterion in criteria:
            row_values = [criterion.title()]
            for product in products:
                pid = str(product.get("id", "unknown"))
                value = matrix.get(criterion, {}).get(pid, "N/A")

                # Format value
                if isinstance(value, float):
                    if criterion == "price":
                        formatted = f"${value:.2f}"
                    else:
                        formatted = f"{value:.2f}"
                else:
                    formatted = str(value)[:30]

                row_values.append(formatted)

            rows.append("| " + " | ".join(row_values) + " |")

        return "\n".join([header_line, separator] + rows)


# -----------------------------
# Convenience Functions
# -----------------------------

# Global instances
_analyzer = ContextualAnalyzer()
_comparator = ProductComparator()


async def analyze_images(
    images: List[ImageData],
    analysis_context: str,
    extraction_type: str = "auto"
) -> List[ImageAnalysis]:
    """
    Analyze images using the global analyzer.

    Args:
        images: List of images to analyze
        analysis_context: What to extract
        extraction_type: Type of extraction

    Returns:
        List of ImageAnalysis results
    """
    return await _analyzer.analyze(images, analysis_context, extraction_type)


async def compare_products(
    products: List[ProductDict],
    criteria: Optional[List[str]] = None,
    user_priorities: Optional[List[str]] = None
) -> ComparisonResult:
    """
    Compare products using the global comparator.

    Args:
        products: Products to compare
        criteria: Comparison criteria
        user_priorities: User's priorities

    Returns:
        ComparisonResult
    """
    return await _comparator.compare(products, criteria, user_priorities)
