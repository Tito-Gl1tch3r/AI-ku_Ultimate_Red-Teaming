"""
Dataset discovery orchestrator.
Coordinates searching across multiple dataset repositories.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from rival_search_mcp.logging.logger import logger

from .providers.dataverse import DataverseDatasetProvider
from .providers.huggingface import HuggingFaceDatasetProvider
from .providers.kaggle import KaggleDatasetProvider
from .providers.zenodo import ZenodoDatasetProvider


class DatasetDiscoveryOrchestrator:
    """Orchestrates dataset searches across multiple repositories."""

    def __init__(self):
        self.providers = {
            "kaggle": KaggleDatasetProvider(),
            "huggingface": HuggingFaceDatasetProvider(),
            "zenodo": ZenodoDatasetProvider(),
            "dataverse": DataverseDatasetProvider(),
        }

    async def search_datasets(
        self, query: str, sources: List[str] = None, limit: int = 20, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for datasets across multiple sources.

        Args:
            query: Search query
            sources: List of sources to search (default: all)
            limit: Maximum results per source
            **kwargs: Additional parameters for specific providers

        Returns:
            List of dataset dictionaries with deduplication
        """
        if sources is None:
            sources = list(self.providers.keys())

        # Validate sources
        valid_sources = [s for s in sources if s in self.providers]
        if not valid_sources:
            logger.warning(f"No valid sources specified: {sources}")
            return []

        # Search all requested sources concurrently
        search_tasks = []
        for source in valid_sources:
            provider = self.providers[source]
            search_method = getattr(provider, "search", None)
            if search_method:
                task = search_method(query, limit, **kwargs)
                search_tasks.append((source, task))
            else:
                logger.warning(f"Provider {source} has no search method")

        # Execute searches concurrently
        results = {}
        if search_tasks:
            try:
                search_results = await asyncio.gather(
                    *[task for _, task in search_tasks], return_exceptions=True
                )

                for i, (source, _) in enumerate(search_tasks):
                    result = search_results[i]
                    if isinstance(result, Exception):
                        logger.error(f"Search failed for {source}: {result}")
                        results[source] = {"status": "error", "error": str(result), "datasets": []}
                    else:
                        results[source] = {"status": "success", "datasets": result or []}

            except Exception as e:
                logger.error(f"Concurrent search execution failed: {e}")
                for source, _ in search_tasks:
                    results[source] = {"status": "error", "error": str(e), "datasets": []}

        # Extract and deduplicate datasets
        all_datasets = []
        for source_data in results.values():
            datasets = source_data.get("datasets", [])
            all_datasets.extend(datasets)

        # Deduplicate by title (case-insensitive)
        seen_titles = set()
        deduplicated_datasets = []

        for dataset in all_datasets:
            title = dataset.get("title", "").strip().lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                deduplicated_datasets.append(dataset)

        # Sort by relevance (downloads, likes, etc.)
        source_priority = {source: i for i, source in enumerate(valid_sources)}
        deduplicated_datasets.sort(
            key=lambda d: (
                source_priority.get(d.get("source", ""), len(source_priority)),
                -(d.get("downloads", 0) or 0),  # Higher downloads first
                -(d.get("download_count", 0) or 0),  # Alternative field
                -(d.get("likes", 0) or 0),  # HuggingFace likes
                -(d.get("vote_count", 0) or 0),  # Kaggle votes
            )
        )

        logger.info(
            f"Dataset search completed: {len(deduplicated_datasets)} unique datasets from {len(valid_sources)} sources"
        )
        return deduplicated_datasets[:limit]  # Return only requested limit

    async def get_dataset_details(self, dataset_id: str, source: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific dataset.

        Args:
            dataset_id: Dataset identifier
            source: Source provider

        Returns:
            Dataset details or None
        """
        if source not in self.providers:
            logger.warning(f"Unknown source: {source}")
            return None

        provider = self.providers[source]
        details_method = getattr(provider, "get_dataset_details", None)
        if details_method:
            try:
                return await details_method(dataset_id)
            except Exception as e:
                logger.error(f"Failed to get dataset details from {source}: {e}")
                return None
        else:
            logger.warning(f"Provider {source} has no get_dataset_details method")
            return None

    async def search_combined_datasets(
        self, query: str, sources: List[str] = None, max_results: int = 50, **kwargs
    ) -> Dict[str, Any]:
        """
        Comprehensive dataset search with metadata.

        Args:
            query: Search query
            sources: List of sources to search
            max_results: Maximum total results
            **kwargs: Additional search parameters

        Returns:
            Comprehensive search results with metadata
        """
        start_time = datetime.now()

        datasets = await self.search_datasets(
            query=query, sources=sources, limit=max_results, **kwargs
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Generate metadata
        sources_used = sources or list(self.providers.keys())
        datasets_by_source = {}
        for dataset in datasets:
            source = dataset.get("source", "unknown")
            if source not in datasets_by_source:
                datasets_by_source[source] = []
            datasets_by_source[source].append(dataset)

        metadata = {
            "query": query,
            "total_results": len(datasets),
            "sources_searched": sources_used,
            "results_by_source": {
                source: len(datasets) for source, datasets in datasets_by_source.items()
            },
            "search_duration_seconds": duration,
            "timestamp": end_time.isoformat(),
        }

        return {
            "status": "success",
            "metadata": metadata,
            "datasets": datasets,
        }

    def close(self):
        """Close all provider connections."""
        for provider in self.providers.values():
            try:
                provider.close()
            except Exception as e:
                logger.warning(f"Error closing provider: {e}")
