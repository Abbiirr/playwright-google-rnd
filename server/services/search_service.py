# services/search_service.py

"""
Search service - handles all search business logic
"""

import asyncio
import random
import logging
from typing import List
from datetime import datetime
from pathlib import Path

from server.models.search import SearchMode, SearchResponse
from server.scrapers.google_session_scraper import GoogleSearchWithSession
from server.scrapers.google_simple_scraper import GoogleSimpleScraper
from server.utils.file_handler import save_search_results

# Configure logging
logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self):
        logger.info("Initializing SearchService")
        self._setup_directories()
        logger.info("SearchService initialized successfully")

    def _setup_directories(self):
        """Create necessary directories"""
        logger.debug("Setting up directories")
        dirs = ['results', 'results/errors', 'results/screenshots',
                'results/debug', 'browser_profiles']
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.debug(f"  Created/verified directory: {dir_path}")
        logger.info("All directories setup complete")

    def _get_available_profiles(self) -> List[str]:
        """Get list of available browser profiles"""
        profiles_dir = Path("browser_profiles")
        if profiles_dir.exists():
            profiles = [p.name for p in profiles_dir.iterdir() if p.is_dir()]
            logger.debug(f"Available profiles: {profiles}")
            return profiles
        return []

    async def search_single(
            self,
            query: str,
            max_results: int = 20,
            mode: SearchMode = SearchMode.SESSION,
            headless: bool = True,
            slowmo: int = 0,
            save_to_file: bool = False,
            profile_name: str = "api_google_profile"
    ) -> SearchResponse:
        """Perform a single search"""
        logger.info(f"search_single called: query='{query}', max_results={max_results}, mode={mode}, headless={headless}, slowmo={slowmo}, save_to_file={save_to_file}, profile_name='{profile_name}'")

        try:
            # Execute search based on mode
            if mode == SearchMode.SESSION:
                logger.info(f"Using SESSION mode scraper with profile: '{profile_name}' and slowmo: {slowmo}")
                # Create scraper instance with specified profile
                session_scraper = GoogleSearchWithSession(profile_name)
                search_data = await session_scraper.search(
                    query, max_results, headless, slowmo
                )
            else:
                logger.info(f"Using SIMPLE mode scraper for query: '{query}' with slowmo: {slowmo}")
                simple_scraper = GoogleSimpleScraper()
                search_data = await simple_scraper.search(
                    query, max_results, slowmo
                )

            logger.debug(f"Search data received, checking for errors")

            # Save to file if requested
            if save_to_file and search_data:
                logger.info(f"Saving search results to file for query: '{query}'")
                try:
                    save_search_results(search_data)
                    logger.info("Search results saved successfully")
                except Exception as e:
                    logger.error(f"Failed to save search results: {e}")

            # Check for errors
            if 'error' in search_data:
                logger.warning(f"Search returned with error for query '{query}': {search_data.get('error')}")
                return SearchResponse(
                    success=False,
                    query=query,
                    timestamp=search_data.get('timestamp', datetime.now().isoformat()),
                    results_count=0,
                    data=search_data,
                    error=str(search_data.get('error', 'Unknown error'))
                )

            results_count = len(search_data.get('organic_results', []))
            logger.info(f"Search successful for query '{query}': {results_count} results")

            return SearchResponse(
                success=True,
                query=query,
                timestamp=search_data.get('timestamp', datetime.now().isoformat()),
                results_count=results_count,
                data=search_data,
                error=None
            )

        except Exception as e:
            logger.error(f"Exception in search_single for query '{query}': {e}", exc_info=True)
            return SearchResponse(
                success=False,
                query=query,
                timestamp=datetime.now().isoformat(),
                results_count=0,
                data={},
                error=str(e)
            )

    async def search_batch(
            self,
            queries: List[str],
            max_results: int = 20,
            mode: SearchMode = SearchMode.SESSION,
            headless: bool = True,
            slowmo: int = 0,
            delay_min: int = 5,
            delay_max: int = 10,
            profile_name: str = "api_google_profile"
    ) -> List[SearchResponse]:
        """Perform batch search"""
        logger.info(f"search_batch called: {len(queries)} queries, mode={mode}, slowmo={slowmo}, delay={delay_min}-{delay_max}s, profile_name='{profile_name}'")
        logger.debug(f"Queries: {queries}")

        results = []

        for i, query in enumerate(queries):
            logger.info(f"Processing query {i+1}/{len(queries)}: '{query}'")

            result = await self.search_single(
                query=query,
                max_results=max_results,
                mode=mode,
                headless=headless,
                slowmo=slowmo,
                save_to_file=False,
                profile_name=profile_name
            )
            results.append(result)
            logger.info(f"Query {i+1}/{len(queries)} completed: success={result.success}")

            # Add delay between requests (except for last query)
            if i < len(queries) - 1:
                delay = random.uniform(delay_min, delay_max)
                logger.info(f"Waiting {delay:.2f} seconds before next query")
                await asyncio.sleep(delay)

        logger.info(f"Batch search completed: {len(results)} queries processed")
        successful = sum(1 for r in results if r.success)
        logger.info(f"Success rate: {successful}/{len(results)} queries")

        return results

