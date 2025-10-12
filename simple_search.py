"""
Simple Google Search Scraper with Anti-Detection
"""

import asyncio
import random
from playwright.async_api import async_playwright

async def search_google(query: str):
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

        try:
            # Go to Google
            await page.goto("https://www.google.com")
            await asyncio.sleep(2)  # Wait for page to settle

            # Search
            search_box = page.locator('[name="q"]')
            await search_box.click()

            # Type with human-like delays
            for char in query:
                await search_box.type(char, delay=random.randint(100, 200))

            await asyncio.sleep(1)
            await page.keyboard.press("Enter")

            # Wait for results
            await asyncio.sleep(5)
            await page.wait_for_selector("#search", timeout=30000)
            await asyncio.sleep(5)

            # Extract results - using the actual selector from your HTML
            results = []

            # Try to get result containers
            result_divs = await page.locator('.wHYlTd').all()

            for i, div in enumerate(result_divs[:10], 1):
                try:
                    # Get title
                    title_elem = div.locator('h3')
                    if await title_elem.count() > 0:
                        title = await title_elem.text_content()

                        # Get link
                        link_elem = div.locator('a[href]').first
                        link = await link_elem.get_attribute('href') if await link_elem.count() > 0 else ""

                        # Get snippet
                        snippet = ""
                        snippet_elem = div.locator('.VwiC3b')
                        if await snippet_elem.count() > 0:
                            snippet = await snippet_elem.text_content()

                        results.append({
                            'position': i,
                            'title': title.strip(),
                            'link': link,
                            'snippet': snippet.strip() if snippet else ""
                        })

                        print(f"[{i}] {title[:60]}...")
                except:
                    continue

            print(f"Found {len(results)} results")
            return results

        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="error.png")
            return []

        finally:
            await browser.close()

async def main():
    results = await search_google("playwright python examples")

    if results:
        print("\nResults:")
        for r in results:
            print(f"\n{r['position']}. {r['title']}")
            print(f"   {r['link'][:80]}...")

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())