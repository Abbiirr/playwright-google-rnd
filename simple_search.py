"""
Enhanced Google Search Scraper with Comprehensive Data Collection
"""

import asyncio
import random
import json
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright

async def search_google(query: str, max_results: int = 20):
    print(f"Searching: {query}")

    async with async_playwright() as p:
        # Launch browser - headless=False reduces detection
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        # Create context with real browser fingerprint
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Inject anti-detection script
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
                # Number of results
                stats = page.locator("#result-stats")
                if await stats.count() > 0:
                    search_data['search_metadata']['result_stats'] = await stats.text_content()

                # Search time
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
                    # Try to get source
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
                    for sl in sitelink_elems[:4]:  # Limit to 4 sitelinks
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

                    # Ad title
                    ad_title = ad.locator('.v0nnCb span').first
                    if await ad_title.count() > 0:
                        ad_data['title'] = await ad_title.text_content()

                    # Ad URL
                    ad_url = ad.locator('.v5yQqb .sVXRqc').first
                    if await ad_url.count() > 0:
                        ad_data['display_url'] = await ad_url.text_content()

                    # Ad description
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

                        # Business name
                        name = item.locator('.dbg0pd span').first
                        if await name.count() > 0:
                            local_data['name'] = await name.text_content()

                        # Rating
                        rating = item.locator('.yi40Hd').first
                        if await rating.count() > 0:
                            local_data['rating'] = await rating.text_content()

                        # Reviews count
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

            return search_data

        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="error.png")
            search_data['error'] = str(e)
            return search_data

        finally:
            await browser.close()


def save_to_json(data, filename=None):
    """Save search data to JSON file"""
    import os

    # Create results directory if it doesn't exist
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)

    if filename is None:
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_safe = "".join(c for c in data['query'] if c.isalnum() or c in (' ', '-', '_'))[:30]
        filename = f"search_{query_safe}_{timestamp}.json"

    # Full path with results directory
    filepath = os.path.join(results_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nData saved to: {filepath}")
    return filepath


async def main():
    # Example search queries
    queries = [
        "python playwright tutorial",
        # "best restaurants near me",  # Will trigger local results
        # "latest AI news",  # May trigger news results
        # "laptop prices"  # May trigger shopping results
    ]

    all_results = []

    for query in queries:
        print(f"\n{'='*60}")
        results = await search_google(query, max_results=20)

        if results:
            all_results.append(results)

            # Save individual search
            save_to_json(results)

            # Add delay between searches to avoid rate limiting
            if len(queries) > 1:
                delay = random.randint(5, 10)
                print(f"Waiting {delay} seconds before next search...")
                await asyncio.sleep(delay)

    # Save combined results
    if len(all_results) > 1:
        combined_data = {
            'searches': all_results,
            'total_searches': len(all_results),
            'timestamp': datetime.now().isoformat()
        }
        save_to_json(combined_data, 'combined_searches.json')

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())