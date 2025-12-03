"""
Budget handler with currency conversion and natural language parsing.

This module parses budget information from natural language text and converts
currencies to USD for consistent filtering across the system.
"""

import re
import logging
from typing import Optional, List, Dict, Any

import sys
import os

# Add parent directory (agents) to path for imports
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

from state import BudgetContext, ProductDict

logger = logging.getLogger(__name__)


# -----------------------------
# Exchange Rates (approximate)
# In production, these should be fetched from an API
# -----------------------------

EXCHANGE_RATES: Dict[str, float] = {
    "USD": 1.0,
    "MXN": 0.058,     # 1 MXN = ~$0.058 USD (peso mexicano)
    "EUR": 1.08,      # 1 EUR = ~$1.08 USD (euro)
    "GBP": 1.27,      # 1 GBP = ~$1.27 USD (libra esterlina)
    "CAD": 0.74,      # 1 CAD = ~$0.74 USD (dólar canadiense)
    "ARS": 0.0012,    # 1 ARS = ~$0.0012 USD (peso argentino)
    "COP": 0.00025,   # 1 COP = ~$0.00025 USD (peso colombiano)
    "CLP": 0.0011,    # 1 CLP = ~$0.0011 USD (peso chileno)
    "PEN": 0.27,      # 1 PEN = ~$0.27 USD (sol peruano)
    "BRL": 0.20,      # 1 BRL = ~$0.20 USD (real brasileño)
}


# -----------------------------
# Currency Detection Patterns
# -----------------------------

# Ordered by specificity (most specific first)
CURRENCY_PATTERNS: List[tuple] = [
    # USD patterns
    (r'(?:us\s*)?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:usd|dolares?|dollars?)?', 'USD'),
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:usd|d[oó]lares?\s*americanos?)', 'USD'),

    # MXN patterns (peso mexicano)
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:pesos?\s*mexicanos?|mxn|mx)', 'MXN'),
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*pesos?(?!\s*(?:argentinos?|colombianos?|chilenos?))', 'MXN'),

    # EUR patterns
    (r'€\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', 'EUR'),
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:euros?|eur)', 'EUR'),

    # GBP patterns
    (r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', 'GBP'),
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:libras?|gbp|pounds?)', 'GBP'),

    # ARS patterns (peso argentino)
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:pesos?\s*argentinos?|ars)', 'ARS'),

    # COP patterns (peso colombiano)
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:pesos?\s*colombianos?|cop)', 'COP'),

    # CLP patterns (peso chileno)
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:pesos?\s*chilenos?|clp)', 'CLP'),

    # PEN patterns (sol peruano)
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:soles?|pen)', 'PEN'),

    # BRL patterns (real brasileño)
    (r'R\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', 'BRL'),
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:reales?|reais|brl)', 'BRL'),

    # CAD patterns
    (r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:d[oó]lares?\s*canadienses?|cad)', 'CAD'),

    # Generic dollar (assume USD)
    (r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', 'USD'),
]


# Per-item indicators
PER_ITEM_INDICATORS = [
    "cada", "each", "por item", "per item", "por producto", "per product",
    "por prenda", "por artículo", "por pieza", "máximo por"
]


class BudgetHandler:
    """
    Handler for parsing budget from natural language and filtering products.

    Examples:
        - "tengo 500 pesos" → BudgetContext(amount=500, currency="MXN", amount_usd=29)
        - "my budget is $100" → BudgetContext(amount=100, currency="USD", amount_usd=100)
        - "máximo 50 euros" → BudgetContext(amount=50, currency="EUR", amount_usd=54)
    """

    def __init__(self, exchange_rates: Optional[Dict[str, float]] = None):
        """
        Initialize with optional custom exchange rates.

        Args:
            exchange_rates: Custom exchange rates dict. Uses defaults if None.
        """
        self.exchange_rates = exchange_rates or EXCHANGE_RATES

    def parse_budget(self, text: str) -> Optional[BudgetContext]:
        """
        Extract budget from user text.

        Args:
            text: User's message text

        Returns:
            BudgetContext if budget found, None otherwise
        """
        text_lower = text.lower()

        for pattern, currency in CURRENCY_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                # Extract and clean the amount
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue

                # Get exchange rate
                rate = self.exchange_rates.get(currency, 1.0)
                amount_usd = amount * rate

                # Check if per-item or total
                is_total = not self._is_per_item(text_lower)

                logger.info(
                    f"Parsed budget: {amount} {currency} = ${amount_usd:.2f} USD "
                    f"({'total' if is_total else 'per-item'})"
                )

                return BudgetContext(
                    amount=amount,
                    currency=currency,
                    amount_usd=round(amount_usd, 2),
                    is_total=is_total,
                    flexibility=0.1  # 10% flexibility by default
                )

        return None

    def _is_per_item(self, text: str) -> bool:
        """Check if the budget is per-item rather than total."""
        return any(indicator in text for indicator in PER_ITEM_INDICATORS)

    def filter_by_budget(
        self,
        products: List[ProductDict],
        budget: BudgetContext,
        num_items: int = 1
    ) -> List[ProductDict]:
        """
        Filter products by budget constraint.

        Args:
            products: List of products to filter
            budget: Budget context with USD amount
            num_items: Expected number of items (for distributing total budget)

        Returns:
            Filtered list of products within budget
        """
        if budget.is_total and num_items > 1:
            # Distribute budget across expected items
            per_item_budget = budget.amount_usd / num_items
        else:
            per_item_budget = budget.amount_usd

        # Apply flexibility
        max_price = per_item_budget * (1 + budget.flexibility)

        filtered = [
            p for p in products
            if p.get("price", float("inf")) <= max_price
        ]

        logger.info(
            f"Budget filter: {len(filtered)}/{len(products)} products "
            f"under ${max_price:.2f}"
        )

        return filtered

    def calculate_total(
        self,
        products: List[ProductDict],
        budget: Optional[BudgetContext] = None
    ) -> Dict[str, Any]:
        """
        Calculate total cost and generate budget breakdown.

        Args:
            products: List of products
            budget: Optional budget context for comparison

        Returns:
            Dictionary with total, breakdown, and markdown table
        """
        total = sum(p.get("price", 0) for p in products)

        # Group by category
        by_category: Dict[str, List[ProductDict]] = {}
        for p in products:
            cat = p.get("category", p.get("product_group", "Other")) or "Other"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(p)

        # Calculate subtotals
        breakdown = {}
        for cat, items in by_category.items():
            subtotal = sum(p.get("price", 0) for p in items)
            breakdown[cat] = {
                "items": items,
                "count": len(items),
                "subtotal": round(subtotal, 2)
            }

        # Generate markdown table
        markdown_lines = [
            "| Categoría | Productos | Subtotal |",
            "|-----------|-----------|----------|"
        ]
        for cat, data in breakdown.items():
            markdown_lines.append(
                f"| {cat} | {data['count']} | ${data['subtotal']:.2f} |"
            )
        markdown_lines.append(f"| **Total** | | **${total:.2f}** |")

        result = {
            "total": round(total, 2),
            "currency": "USD",
            "breakdown": breakdown,
            "markdown_table": "\n".join(markdown_lines),
            "product_count": len(products)
        }

        # Add budget comparison if provided
        if budget:
            result["budget"] = {
                "original_amount": budget.amount,
                "original_currency": budget.currency,
                "budget_usd": budget.amount_usd,
                "remaining": round(budget.amount_usd - total, 2),
                "within_budget": total <= budget.amount_usd * (1 + budget.flexibility)
            }

        return result


# -----------------------------
# Convenience Functions
# -----------------------------

# Global handler instance
_handler = BudgetHandler()


def parse_budget(text: str) -> Optional[BudgetContext]:
    """
    Parse budget from text using the global handler.

    Args:
        text: User's message text

    Returns:
        BudgetContext if budget found, None otherwise
    """
    return _handler.parse_budget(text)


def filter_products_by_budget(
    products: List[ProductDict],
    budget: BudgetContext,
    num_items: int = 1
) -> List[ProductDict]:
    """
    Filter products by budget using the global handler.

    Args:
        products: List of products to filter
        budget: Budget context
        num_items: Expected number of items

    Returns:
        Filtered list of products
    """
    return _handler.filter_by_budget(products, budget, num_items)


def calculate_budget_breakdown(
    products: List[ProductDict],
    budget: Optional[BudgetContext] = None
) -> Dict[str, Any]:
    """
    Calculate budget breakdown using the global handler.

    Args:
        products: List of products
        budget: Optional budget context

    Returns:
        Budget breakdown dictionary
    """
    return _handler.calculate_total(products, budget)
