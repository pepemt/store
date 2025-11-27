"""Vision node for image analysis using Llama 3.2 Vision via OCI SDK"""
import logging
import sys
import os
import time
import asyncio
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import oci
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import (
    ChatDetails,
    OnDemandServingMode,
    GenericChatRequest,
    UserMessage,
    TextContent,
    ImageContent,
    ImageUrl,
)

from models import AgentState

logger = logging.getLogger(__name__)

# OCI client initialization (singleton pattern)
_oci_vision_client = None


def get_oci_vision_client():
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
            logger.info(f"OCI Vision client initialized with endpoint: {service_endpoint}")
        except Exception as e:
            logger.error(f"Failed to initialize OCI Vision client: {e}")
            raise
    return _oci_vision_client


async def vision_node(state: AgentState) -> dict:
    """
    Analyze image using Llama 3.2 90B Vision model via OCI SDK.
    Generates a fashion-focused description of clothing/accessories.
    """
    start_time = time.time()

    image_data = state.get("image_data")
    image_mime_type = state.get("image_mime_type", "image/jpeg")

    # Get user message if any (clean up [imagen adjunta] marker)
    user_message = ""
    if state.get("messages"):
        last_msg = state["messages"][-1]
        raw_message = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
        # Remove [imagen adjunta] marker that confuses the vision model
        user_message = raw_message.replace("[imagen adjunta]", "").strip()

    logger.info("=" * 80)
    logger.info("VISION NODE START")
    logger.info(f"   Image MIME type: {image_mime_type}")
    logger.info(f"   User context: {user_message[:100] if user_message else 'No text provided'}")
    logger.info("=" * 80)

    if not image_data:
        logger.warning("No image data found in state")
        return {"image_description": None, "has_image": False}

    # Log image size for debugging
    image_size_kb = len(image_data) * 3 // 4 // 1024
    logger.info(f"   Image size: ~{image_size_kb}KB (base64 length: {len(image_data)})")

    try:
        # Build vision prompt - focused on fashion/clothing
        # Note: Llama 3.2 Vision only supports English for image+text tasks
        has_user_context = bool(user_message and user_message.strip())

        if has_user_context:
            vision_prompt = """You are a fashion product analyst for an online clothing store.

Analyze this image and describe in detail:
1. Type of clothing/accessory (shirt, pants, dress, shoes, bag, jewelry, etc.)
2. Color(s) and patterns (solid, stripes, floral, etc.)
3. Style (casual, formal, sporty, elegant, etc.)
4. Material if visible (cotton, leather, denim, silk, etc.)
5. Key features (buttons, zipper, collar type, etc.)

Be concise but detailed. Focus on attributes useful for product search.
Respond in Spanish.

The user said: """ + user_message + """

Consider their context when describing the product."""
        else:
            vision_prompt = """You are a fashion product analyst for an online clothing store.

Analyze this image and describe in detail:
1. Type of clothing/accessory (shirt, pants, dress, shoes, bag, jewelry, etc.)
2. Color(s) and patterns (solid, stripes, floral, etc.)
3. Style (casual, formal, sporty, elegant, etc.)
4. Material if visible (cotton, leather, denim, silk, etc.)
5. Key features (buttons, zipper, collar type, etc.)

Be concise but detailed. Respond in Spanish.

After describing the image, ask the user what they would like to do:
- Search for similar products?
- Get more information about this type of item?
- Something else?"""

        # Get OCI client
        client = get_oci_vision_client()

        # Build the multimodal message using OCI SDK format
        # Convert mime type to format OCI expects
        mime_type_clean = image_mime_type.replace("image/", "")
        if mime_type_clean == "jpeg":
            mime_type_clean = "jpg"

        image_url = f"data:image/{mime_type_clean};base64,{image_data}"

        # Create multimodal content - IMAGE FIRST for better Llama Vision processing
        content = [
            ImageContent(image_url=ImageUrl(url=image_url)),
            TextContent(text=vision_prompt)
        ]

        # Create user message with multimodal content
        user_msg = UserMessage(content=content)

        # Build chat request using GenericChatRequest for Llama models
        chat_request = GenericChatRequest(
            messages=[user_msg],
            max_tokens=500,
            temperature=0.3,
            top_p=0.9,
            is_stream=False
        )

        # Build chat details
        chat_details = ChatDetails(
            compartment_id=os.getenv("OCI_GENAI_COMPARTMENT_ID"),
            serving_mode=OnDemandServingMode(
                model_id=os.getenv("OCI_GENAI_VISION_MODEL_ID", "meta.llama-3.2-90b-vision-instruct")
            ),
            chat_request=chat_request
        )

        logger.info("Calling OCI Vision API...")

        # Run synchronous OCI call in executor to not block async loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat(chat_details)
        )

        # Extract response content
        if response.data and response.data.chat_response:
            chat_response = response.data.chat_response
            if hasattr(chat_response, 'choices') and chat_response.choices:
                first_choice = chat_response.choices[0]
                if hasattr(first_choice, 'message') and first_choice.message:
                    if hasattr(first_choice.message, 'content'):
                        # Content can be a list or string
                        content = first_choice.message.content
                        if isinstance(content, list):
                            image_description = " ".join(
                                c.text if hasattr(c, 'text') else str(c)
                                for c in content
                            )
                        else:
                            image_description = str(content)
                    else:
                        image_description = str(first_choice.message)
                else:
                    image_description = str(first_choice)
            else:
                image_description = str(chat_response)
        else:
            logger.warning("Empty response from OCI Vision API")
            image_description = "[No se pudo obtener descripción de la imagen]"

        image_description = image_description.strip()

        # Validate response - detect corrupted/invalid responses (e.g., "!!!..." or empty)
        if not image_description or len(image_description) < 10:
            logger.warning(f"Vision response too short: '{image_description}'")
            image_description = "[No se pudo obtener una descripción válida. Por favor, describe lo que buscas.]"
        elif re.match(r'^[!?.,:;\s]+$', image_description):
            logger.warning(f"Vision response contains only punctuation: '{image_description[:50]}'")
            image_description = "[El modelo no pudo procesar la imagen correctamente. Por favor, intenta con otra imagen o describe lo que buscas.]"

        elapsed = time.time() - start_time
        logger.info(f"Vision analysis complete in {elapsed:.2f}s")
        logger.info(f"Description preview: {image_description[:200]}...")

        return {
            "image_description": image_description,
            "has_image": True
        }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Vision node error after {elapsed:.2f}s: {e}", exc_info=True)
        return {
            "image_description": "[No pude analizar la imagen. Por favor, intenta de nuevo o describe lo que buscas.]",
            "has_image": True
        }
