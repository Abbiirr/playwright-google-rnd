# scrapers/google_simple_scraper.py

"""
Google Simple Scraper Adapter
"""

import sys
import asyncio
import random
import logging
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix for Windows asyncio + Playwright subprocess issues
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    logger.info("Windows asyncio event loop policy set to ProactorEventLoopPolicy")


class GoogleSimpleScraper:
    def __init__(self):
        logger.info("Initialized GoogleSimpleScraper")

    async def search(self, query: str, max_results: int = 20, slowmo: int = 0):
        """Simple Google search without persistent session"""
        logger.info(f"Starting simple search for query: '{query}' (max_results={max_results}, slowmo={slowmo})")

        async with async_playwright() as p:
            logger.info("Playwright context manager started")

            try:
                logger.info(f"Launching Chromium browser with slowmo={slowmo}")
                browser = await p.chromium.launch(
                    headless=False,
                    slow_mo=slowmo,
                    args=['--disable-blink-features=AutomationControlled']
                )
                logger.info("Browser launched successfully")

                logger.debug("Creating browser context")
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                logger.info("Browser context created")

                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                logger.debug("Anti-detection script injected")

                page = await context.new_page()
                logger.info("New page created")

                search_data = {
                    'query': query,
                    'timestamp': datetime.now().isoformat(),
                    'search_metadata': {},
                    'organic_results': [],
                    'people_also_ask': [],
                    'related_searches': [],
                    'featured_snippet': None,
                    'knowledge_panel': None,
                    'ads': [],
                    'local_results': [],
                    'video_results': [],
                    'news_results': [],
                    'shopping_results': []
                }

                try:
                    logger.info("Navigating to Google.com")
                    await page.goto("https://www.google.com")
                    await asyncio.sleep(2)
                    logger.info("Successfully loaded Google.com")

                    logger.info(f"Searching for: '{query}'")
                    search_box = page.locator('[name="q"]')
                    await search_box.click()
                    logger.debug("Search box clicked")

                    logger.debug("Typing query character by character")
                    for char in query:
                        await search_box.type(char, delay=random.randint(100, 200))

                    await asyncio.sleep(1)
                    logger.debug("Pressing Enter to submit search")
                    await page.keyboard.press("Enter")

                    logger.info("Waiting for search results to load")
                    await page.wait_for_selector("#search", timeout=50000)
                    await asyncio.sleep(2)
                    logger.info("Search results loaded successfully")

                    # Search metadata
                    try:
                        logger.debug("Extracting search metadata")
                        stats = page.locator("#result-stats")
                        if await stats.count() > 0:
                            search_data['search_metadata']['result_stats'] = await stats.text_content()
                            logger.info(f"Search stats: {search_data['search_metadata']['result_stats']}")
                        search_data['search_metadata']['url'] = page.url
                        logger.debug(f"Current URL: {page.url}")
                    except Exception as e:
                        logger.warning(f"Error extracting search metadata: {e}")

                    # Organic results
                    logger.info("Extracting organic search results")
                    result_divs = await page.locator('.wHYlTd, .g').all()
                    logger.info(f"Found {len(result_divs)} potential result elements")

                    extracted_count = 0
                    for i, div in enumerate(result_divs[:max_results], 1):
                        try:
                            logger.debug(f"Processing result #{i}")
                            result = {'position': i}

                            title_elem = div.locator('h3').first
                            if await title_elem.count() > 0:
                                result['title'] = await title_elem.text_content()
                                logger.debug(f"  Title: {result['title'][:50]}...")

                            link_elem = div.locator('a[href]').first
                            if await link_elem.count() > 0:
                                result['link'] = await link_elem.get_attribute('href')
                                result['domain'] = urlparse(result['link']).netloc if result['link'] else ""
                                logger.debug(f"  Link: {result['link']}")

                            snippet_elem = div.locator('.VwiC3b, [data-sncf="1"]').first
                            if await snippet_elem.count() > 0:
                                result['snippet'] = await snippet_elem.text_content()
                                logger.debug(f"  Snippet: {result['snippet'][:50]}...")

                            if 'title' in result and result['title']:
                                search_data['organic_results'].append(result)
                                extracted_count += 1
                                logger.debug(f"  Result #{i} added successfully")
                            else:
                                logger.debug(f"  Result #{i} skipped (no title)")
                        except Exception as e:
                            logger.warning(f"Error extracting result #{i}: {e}")
                            continue

                    logger.info(f"Successfully extracted {extracted_count} organic results")
                    logger.info(f"Search completed successfully for query: '{query}'")
                    return search_data

                except Exception as e:
                    logger.error(f"Error during search execution: {e}", exc_info=True)
                    search_data['error'] = str(e)
                    return search_data

                finally:
                    logger.debug("Closing browser")
                    await browser.close()
                    logger.info("Browser closed")

            except Exception as e:
                logger.error(f"Fatal error in search method: {e}", exc_info=True)
                raise
