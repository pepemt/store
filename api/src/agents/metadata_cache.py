
"""
Metadata cache for database categories and values.
Preloads and caches unique values from the database for faster agent decisions.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func
from database.lib import Database
from database.models import Article

logger = logging.getLogger(__name__)


class MetadataCache:
    """
    Caches database metadata like categories, colors, departments, etc.
    Refreshes periodically to stay in sync with the database.
    """

    def __init__(self, ttl_hours: int = 24):
        self.ttl_hours = ttl_hours
        self.last_refresh: Optional[datetime] = None
        self._cache: Dict[str, List[str]] = {}
        logger.info(f"MetadataCache initialized with TTL={ttl_hours}h")

    def is_stale(self) -> bool:
        """Check if cache needs refresh."""
        if self.last_refresh is None:
            return True
        age = datetime.utcnow() - self.last_refresh
        return age > timedelta(hours=self.ttl_hours)

    async def refresh(self, force: bool = False):
        """Refresh cache from database."""
        if not force and not self.is_stale():
            logger.debug("Cache is fresh, skipping refresh")
            return

        logger.info("Refreshing metadata cache from database...")

        try:
            async with Database.get_session() as session:
                # Get unique categories (limit to 30 most common)
                categories = await self._get_top_values(
                    session, Article.product_type_name, limit=30
                )

                # Get unique departments (limit to 20 most common)
                departments = await self._get_top_values(
                    session, Article.department_name, limit=20
                )

                # Get unique product groups (limit to 25 most common)
                product_groups = await self._get_top_values(
                    session, Article.product_group_name, limit=25
                )

                # Get unique colors (limit to 20 most common)
                colors = await self._get_top_values(
                    session, Article.colour_group_name, limit=20
                )

                # Store in cache
                self._cache = {
                    "categories": categories,
                    "departments": departments,
                    "product_groups": product_groups,
                    "colors": colors
                }

                self.last_refresh = datetime.utcnow()

                logger.info(
                    f"Cache refreshed: {len(categories)} categories, "
                    f"{len(departments)} departments, "
                    f"{len(product_groups)} product_groups, "
                    f"{len(colors)} colors"
                )

        except Exception as e:
            logger.error(f"Error refreshing metadata cache: {e}", exc_info=True)
            # Keep old cache if refresh fails
            if not self._cache:
                # Initialize with empty lists if first refresh fails
                self._cache = {
                    "categories": [],
                    "departments": [],
                    "product_groups": [],
                    "colors": []
                }

    async def _get_top_values(
        self, session, column, limit: int = 20
    ) -> List[str]:
        """Get top N most common values for a column."""
        try:
            stmt = (
                select(column, func.count().label("count"))
                .group_by(column)
                .order_by(func.count().desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            values = [row[0] for row in result.fetchall() if row[0]]
            return values
        except Exception as e:
            logger.error(f"Error getting top values for column: {e}")
            return []

    async def get_categories(self) -> List[str]:
        """Get list of available categories."""
        await self.refresh()
        return self._cache.get("categories", [])

    async def get_departments(self) -> List[str]:
        """Get list of available departments."""
        await self.refresh()
        return self._cache.get("departments", [])

    async def get_product_groups(self) -> List[str]:
        """Get list of available product groups."""
        await self.refresh()
        return self._cache.get("product_groups", [])

    async def get_colors(self) -> List[str]:
        """Get list of available colors."""
        await self.refresh()
        return self._cache.get("colors", [])

    async def get_all_metadata(self) -> Dict[str, List[str]]:
        """Get all cached metadata."""
        await self.refresh()
        return self._cache.copy()

    def get_formatted_context(self) -> str:
        """Get formatted string of available values for prompts."""
        if not self._cache:
            return "No metadata available yet."

        lines = []

        if self._cache.get("categories"):
            lines.append(f"Available Categories: {', '.join(self._cache['categories'][:15])}")

        if self._cache.get("departments"):
            lines.append(f"Available Departments: {', '.join(self._cache['departments'][:10])}")

        if self._cache.get("product_groups"):
            lines.append(f"Available Product Groups: {', '.join(self._cache['product_groups'][:12])}")

        if self._cache.get("colors"):
            lines.append(f"Available Colors: {', '.join(self._cache['colors'])}")

        return "\n".join(lines)


# Global instance
_metadata_cache: Optional[MetadataCache] = None


def get_metadata_cache() -> MetadataCache:
    """Get or create the global metadata cache instance."""
    global _metadata_cache
    if _metadata_cache is None:
        _metadata_cache = MetadataCache(ttl_hours=24)
    return _metadata_cache
