"""
Google Search Scraper with Session Management - Fixed
"""

import asyncio
import random
import json
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright


def setup_directories():
    """Create organized directory structure"""
    import os

    dirs = {
        'results': 'results',
        'errors': 'results/errors',
        'screenshots': 'results/screenshots',
        'debug': 'results/debug',
        'profiles': 'browser_profiles'
    }

    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)

    return dirs

class GoogleSearchWithSession:
    def __init__(self, profile_name="google_search_profile"):
        self.profile_name = profile_name
        self.dirs = setup_directories()  # Add this
        self.profiles_dir = Path(self.dirs['profiles'])
        self.profile_path = self.profiles_dir / profile_name
        self.state_file = self.profile_path / "state.json"
        self.profile_path.mkdir(parents=True, exist_ok=True)

    async def search_google_with_session(self, query: str, max_results: int = 20, headless=False):
        """Search Google using persistent profile"""

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_path),
                headless=headless,
                args=['--disable-blink-features=AutomationControlled'],
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page = await context.new_page()

            # Data structure for comprehensive collection
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
                # Go to Google
                await page.goto("https://www.google.com")
                await asyncio.sleep(2)

                # Handle cookie consent
                try:
                    accept_btn = page.locator('button:has-text("Accept all")')
                    if await accept_btn.count() > 0:
                        await accept_btn.click()
                        await asyncio.sleep(1)
                except:
                    pass

                # Search
                search_box = page.locator('[name="q"]')
                await search_box.click()

                # Type with human-like delays
                for char in query:
                    await search_box.type(char, delay=random.randint(100, 200))

                await asyncio.sleep(1)
                await page.keyboard.press("Enter")

                # Wait for results
                await page.wait_for_selector("#search", timeout=50000)
                await asyncio.sleep(2)

                # 1. Extract search metadata
                try:
                    stats = page.locator("#result-stats")
                    if await stats.count() > 0:
                        search_data['search_metadata']['result_stats'] = await stats.text_content()
                    search_data['search_metadata']['url'] = page.url
                except:
                    pass

                # 2. Extract featured snippet
                try:
                    featured = page.locator('[data-attrid="wa:/description"]')
                    if await featured.count() > 0:
                        search_data['featured_snippet'] = {
                            'text': await featured.text_content(),
                            'source': None
                        }
                        source_link = page.locator('[data-attrid="wa:/description"] ~ a')
                        if await source_link.count() > 0:
                            search_data['featured_snippet']['source'] = await source_link.get_attribute('href')
                except:
                    pass

                # 3. Extract organic results
                result_divs = await page.locator('.wHYlTd, .g').all()

                for i, div in enumerate(result_divs[:max_results], 1):
                    try:
                        result = {'position': i}

                        # Title
                        title_elem = div.locator('h3').first
                        if await title_elem.count() > 0:
                            result['title'] = await title_elem.text_content()

                        # Link
                        link_elem = div.locator('a[href]').first
                        if await link_elem.count() > 0:
                            result['link'] = await link_elem.get_attribute('href')
                            result['domain'] = urlparse(result['link']).netloc if result['link'] else ""

                        # Snippet
                        snippet_elem = div.locator('.VwiC3b, [data-sncf="1"]').first
                        if await snippet_elem.count() > 0:
                            result['snippet'] = await snippet_elem.text_content()

                        # Date (if available)
                        date_elem = div.locator('.LEwnzc').first
                        if await date_elem.count() > 0:
                            result['date'] = await date_elem.text_content()

                        # Sitelinks (if available)
                        sitelinks = []
                        sitelink_elems = await div.locator('.HiHjCd a').all()
                        for sl in sitelink_elems[:4]:
                            sl_text = await sl.text_content()
                            sl_href = await sl.get_attribute('href')
                            if sl_text and sl_href:
                                sitelinks.append({'text': sl_text, 'link': sl_href})

                        if sitelinks:
                            result['sitelinks'] = sitelinks

                        # Rich snippets (ratings, reviews, price)
                        rating_elem = div.locator('[aria-label*="Rated"]').first
                        if await rating_elem.count() > 0:
                            result['rating'] = await rating_elem.get_attribute('aria-label')

                        if 'title' in result and result['title']:
                            search_data['organic_results'].append(result)
                            print(f"[{i}] {result['title'][:60]}...")
                    except Exception as e:
                        continue

                # 4. Extract "People also ask"
                try:
                    paa_items = await page.locator('[data-sgrd="true"]').all()
                    for paa in paa_items[:6]:
                        question = await paa.text_content()
                        if question:
                            search_data['people_also_ask'].append(question.strip())
                except:
                    pass

                # 5. Extract related searches
                try:
                    related = await page.locator('a[data-ved] div.s75CSd').all()
                    for rel in related[:8]:
                        rel_text = await rel.text_content()
                        if rel_text:
                            search_data['related_searches'].append(rel_text.strip())
                except:
                    pass

                # 6. Extract video results
                try:
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
                except:
                    pass

                # 7. Extract ads (if present)
                try:
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
                except:
                    pass

                # 8. Extract local results (maps pack)
                try:
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
                except:
                    pass

                print(f"\nData collection complete:")
                print(f"- Organic results: {len(search_data['organic_results'])}")
                print(f"- People also ask: {len(search_data['people_also_ask'])}")
                print(f"- Related searches: {len(search_data['related_searches'])}")
                print(f"- Video results: {len(search_data['video_results'])}")
                print(f"- Ads: {len(search_data['ads'])}")
                print(f"- Local results: {len(search_data['local_results'])}")

                # Save state after successful search
                await context.storage_state(path=str(self.state_file))
                print(f"✓ Session saved to: {self.state_file}")

                return search_data

            except Exception as e:
                print(f"Error during search: {e}")

                # Save error screenshot
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = Path(self.dirs['screenshots']) / f"error_{timestamp}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"📸 Error screenshot saved: {screenshot_path}")

                # Save error details
                error_data = {
                    'timestamp': datetime.now().isoformat(),
                    'query': query,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'screenshot': str(screenshot_path),
                    'page_url': page.url if page else None
                }

                error_file = Path(self.dirs['errors']) / f"error_{timestamp}.json"
                with open(error_file, 'w', encoding='utf-8') as f:
                    json.dump(error_data, f, indent=2, ensure_ascii=False)
                print(f"❌ Error details saved: {error_file}")

                search_data['error'] = error_data
                return search_data

            finally:
                await context.close()

    async def batch_search(self, queries, delay_range=(5, 10)):
        """Perform multiple searches with delays"""
        all_results = []

        for i, query in enumerate(queries, 1):
            print(f"\n[{i}/{len(queries)}] Searching: {query}")

            result = await self.search_google_with_session(query, headless=False)

            if result:
                all_results.append(result)

                # Save individual result
                save_to_json(result, dirs=self.dirs)

            # Delay between searches (except for last one)
            if i < len(queries):
                delay = random.randint(*delay_range)
                print(f"⏳ Waiting {delay} seconds...")
                await asyncio.sleep(delay)

        # Save combined results
        if all_results:
            combined = {
                'searches': all_results,
                'total': len(all_results),
                'timestamp': datetime.now().isoformat()
            }

            combined_file = f"batch_search_{datetime.now():%Y%m%d_%H%M%S}.json"
            save_to_json(combined, combined_file, dirs=self.dirs)

        return all_results


def save_to_json(data, filename=None, dirs=None):
    """Save search data to JSON file"""
    import os

    if dirs is None:
        dirs = setup_directories()

    results_dir = dirs['results']

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_safe = "".join(c for c in data['query'] if c.isalnum() or c in (' ', '-', '_'))[:30]
        filename = f"search_{query_safe}_{timestamp}.json"

    filepath = os.path.join(results_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nData saved to: {filepath}")
    return filepath


async def main():
    scraper = GoogleSearchWithSession("my_google_profile")

    print("=== Running Search ===")
    result = await scraper.search_google_with_session("Python asyncio tutorial")

    if result:
        print(f"\n✅ Search completed successfully!")
        save_to_json(result)

    # Batch search example
    print("\n=== Batch Search ===")
    queries = [
        "playwright python examples",
        "web scraping best practices",
        "asyncio vs threading python"
    ]

    results = await scraper.batch_search(queries, delay_range=(5, 10))
    print(f"\n✅ Completed {len(results)} searches")


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())