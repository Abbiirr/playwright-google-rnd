# scrapers/google_session_scraper.py

"""
Google Session Scraper Adapter
"""

import sys
import asyncio
import random
import json
import logging
from pathlib import Path
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


class GoogleSearchWithSession:
    def __init__(self, profile_name="google_search_profile"):
        self.profile_name = profile_name
        self.profiles_dir = Path("browser_profiles")
        self.profile_path = self.profiles_dir / profile_name
        self.state_file = self.profile_path / "state.json"
        self.profile_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized GoogleSearchWithSession with profile: {profile_name}")
        logger.info(f"Profile path: {self.profile_path}")

    async def search(self, query: str, max_results: int = 20, headless=False, slowmo: int = 0):
        """Search Google using persistent profile"""
        logger.info(f"Starting search for query: '{query}' (max_results={max_results}, headless={headless}, slowmo={slowmo})")

        async with async_playwright() as p:
            logger.info("Playwright context manager started")

            try:
                logger.info(f"Launching Chromium with persistent context from: {self.profile_path}, slowmo={slowmo}")
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_path),
                    headless=headless,
                    slow_mo=slowmo,
                    args=['--disable-blink-features=AutomationControlled'],
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                logger.info("Browser context launched successfully")

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

                    # Handle cookie consent
                    try:
                        logger.debug("Checking for cookie consent dialog")
                        accept_btn = page.locator('button:has-text("Accept all")')
                        if await accept_btn.count() > 0:
                            logger.info("Cookie consent dialog found, clicking 'Accept all'")
                            await accept_btn.click()
                            await asyncio.sleep(1)
                            logger.info("Cookie consent accepted")
                        else:
                            logger.debug("No cookie consent dialog found")
                    except Exception as e:
                        logger.warning(f"Error handling cookie consent: {e}")

                    # Search
                    logger.info(f"Searching for: '{query}'")
                    search_box = page.locator('[name="q"]')
                    await search_box.click()
                    logger.debug("Search box clicked")

                    # Add small delay after clicking
                    await asyncio.sleep(0.5)

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

                    # Extract search metadata
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

                    # Extract featured snippet
                    try:
                        logger.debug("Checking for featured snippet")
                        featured = page.locator('[data-attrid="wa:/description"]')
                        if await featured.count() > 0:
                            search_data['featured_snippet'] = {
                                'text': await featured.text_content(),
                                'source': None
                            }
                            logger.info("Featured snippet found")
                            source_link = page.locator('[data-attrid="wa:/description"] ~ a')
                            if await source_link.count() > 0:
                                search_data['featured_snippet']['source'] = await source_link.get_attribute('href')
                                logger.debug(f"Featured snippet source: {search_data['featured_snippet']['source']}")
                        else:
                            logger.debug("No featured snippet found")
                    except Exception as e:
                        logger.warning(f"Error extracting featured snippet: {e}")

                    # Extract organic results
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

                            date_elem = div.locator('.LEwnzc').first
                            if await date_elem.count() > 0:
                                result['date'] = await date_elem.text_content()
                                logger.debug(f"  Date: {result['date']}")

                            # Sitelinks
                            sitelinks = []
                            sitelink_elems = await div.locator('.HiHjCd a').all()
                            for sl in sitelink_elems[:4]:
                                sl_text = await sl.text_content()
                                sl_href = await sl.get_attribute('href')
                                if sl_text and sl_href:
                                    sitelinks.append({'text': sl_text, 'link': sl_href})

                            if sitelinks:
                                result['sitelinks'] = sitelinks
                                logger.debug(f"  Found {len(sitelinks)} sitelinks")

                            rating_elem = div.locator('[aria-label*="Rated"]').first
                            if await rating_elem.count() > 0:
                                result['rating'] = await rating_elem.get_attribute('aria-label')
                                logger.debug(f"  Rating: {result['rating']}")

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

                    # Extract People also ask
                    try:
                        logger.debug("Extracting 'People also ask' section")
                        paa_items = await page.locator('[data-sgrd="true"]').all()
                        for paa in paa_items[:6]:
                            question = await paa.text_content()
                            if question:
                                search_data['people_also_ask'].append(question.strip())
                        logger.info(f"Extracted {len(search_data['people_also_ask'])} 'People also ask' questions")
                    except Exception as e:
                        logger.warning(f"Error extracting 'People also ask': {e}")

                    # Extract related searches
                    try:
                        logger.debug("Extracting related searches")
                        related = await page.locator('a[data-ved] div.s75CSd').all()
                        for rel in related[:8]:
                            rel_text = await rel.text_content()
                            if rel_text:
                                search_data['related_searches'].append(rel_text.strip())
                        logger.info(f"Extracted {len(search_data['related_searches'])} related searches")
                    except Exception as e:
                        logger.warning(f"Error extracting related searches: {e}")

                    # Extract video results
                    try:
                        logger.debug("Extracting video results")
                        video_section = page.locator('video-voyager')
                        if await video_section.count() > 0:
                            videos = await video_section.locator('.MjjYud').all()
                            for video in videos[:3]:
                                video_data = {}
                                title = video.locator('h3')
                                if await title.count() > 0:
                                    video_data['title'] = await title.text_content()

                                duration = video.locator('.J1mWY')
                                if await duration.count() > 0:
                                    video_data['duration'] = await duration.text_content()

                                source = video.locator('.pcJO7e')
                                if await source.count() > 0:
                                    video_data['source'] = await source.text_content()

                                if video_data:
                                    search_data['video_results'].append(video_data)
                            logger.info(f"Extracted {len(search_data['video_results'])} video results")
                        else:
                            logger.debug("No video results section found")
                    except Exception as e:
                        logger.warning(f"Error extracting video results: {e}")

                    # Extract ads
                    try:
                        logger.debug("Extracting ads")
                        ad_containers = await page.locator('[data-text-ad="1"]').all()
                        for ad in ad_containers[:5]:
                            ad_data = {}

                            ad_title = ad.locator('.v0nnCb span').first
                            if await ad_title.count() > 0:
                                ad_data['title'] = await ad_title.text_content()

                            ad_url = ad.locator('.v5yQqb .sVXRqc').first
                            if await ad_url.count() > 0:
                                ad_data['display_url'] = await ad_url.text_content()

                            ad_desc = ad.locator('.MUxGbd').first
                            if await ad_desc.count() > 0:
                                ad_data['description'] = await ad_desc.text_content()

                            if ad_data:
                                search_data['ads'].append(ad_data)
                        logger.info(f"Extracted {len(search_data['ads'])} ads")
                    except Exception as e:
                        logger.warning(f"Error extracting ads: {e}")

                    # Extract local results
                    try:
                        logger.debug("Extracting local results")
                        local_pack = page.locator('[data-hveid][jscontroller][jsaction][jsowner]')
                        if await local_pack.count() > 0:
                            local_items = await local_pack.locator('.VkpGBb').all()
                            for item in local_items[:3]:
                                local_data = {}

                                name = item.locator('.dbg0pd span').first
                                if await name.count() > 0:
                                    local_data['name'] = await name.text_content()

                                rating = item.locator('.yi40Hd').first
                                if await rating.count() > 0:
                                    local_data['rating'] = await rating.text_content()

                                reviews = item.locator('.RDApEe').first
                                if await reviews.count() > 0:
                                    local_data['reviews'] = await reviews.text_content()

                                if local_data:
                                    search_data['local_results'].append(local_data)
                            logger.info(f"Extracted {len(search_data['local_results'])} local results")
                        else:
                            logger.debug("No local results found")
                    except Exception as e:
                        logger.warning(f"Error extracting local results: {e}")

                    # Save state
                    logger.debug(f"Saving browser state to: {self.state_file}")
                    await context.storage_state(path=str(self.state_file))
                    logger.info("Browser state saved successfully")

                    logger.info(f"Search completed successfully for query: '{query}'")
                    return search_data

                except Exception as e:
                    logger.error(f"Error during search execution: {e}", exc_info=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = Path("results/screenshots") / f"error_{timestamp}.png"

                    try:
                        await page.screenshot(path=str(screenshot_path), full_page=True)
                        logger.info(f"Error screenshot saved to: {screenshot_path}")
                    except Exception as screenshot_error:
                        logger.error(f"Failed to save error screenshot: {screenshot_error}")

                    search_data['error'] = {
                        'timestamp': datetime.now().isoformat(),
                        'query': query,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'screenshot': str(screenshot_path)
                    }
                    return search_data

                finally:
                    logger.debug("Closing browser context")
                    await context.close()
                    logger.info("Browser context closed")

            except Exception as e:
                logger.error(f"Fatal error in search method: {e}", exc_info=True)
                raise
