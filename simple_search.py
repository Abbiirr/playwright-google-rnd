"""
Simple Google Search with Playwright - No FastAPI
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from playwright.async_api import async_playwright, Page

# Setup paths
STORAGE_STATE_PATH = Path("auth.json")
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)


async def handle_consent(page: Page):
    """Click Google consent if present"""
    try:
        consent_button = await page.wait_for_selector("#L2AGLb", timeout=2000)
        if consent_button:
            await consent_button.click()
            await page.wait_for_load_state("networkidle", timeout=5000)
            print("✓ Accepted consent")
    except:
        pass  # No consent needed


async def detect_captcha(page: Page) -> bool:
    """Check for CAPTCHA/unusual traffic"""
    indicators = ["text=/unusual traffic/i", "#captcha", ".g-recaptcha"]
    for indicator in indicators:
        if await page.query_selector(indicator):
            return True
    return False


async def parse_results(page: Page, max_results: int = 10) -> List[Dict]:
    """Extract search results"""
    results = []

    # Wait for results container
    await page.wait_for_selector("#search", timeout=10000)

    # Get all organic results
    elements = await page.query_selector_all("#search a:has(h3)")

    for i, element in enumerate(elements[:max_results]):
        try:
            # Title
            h3 = await element.query_selector("h3")
            title = await h3.inner_text() if h3 else ""

            # URL
            url = await element.get_attribute("href") or ""

            # Snippet
            parent = await element.evaluate_handle("el => el.closest('.g')")
            snippet_elem = await parent.query_selector(".VwiC3b, [data-sncf='2']")
            snippet = await snippet_elem.inner_text() if snippet_elem else ""

            if title and url:
                results.append({
                    "position": i + 1,
                    "title": title.strip(),
                    "url": url,
                    "snippet": snippet.strip()
                })
                print(f"  [{i + 1}] {title[:60]}...")
        except Exception as e:
            continue

    return results


async def search_google(query: str, max_results: int = 10):
    """Perform a single Google search"""
    print(f"\n🔍 Searching: '{query}'")

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=1000,
            args=['--disable-blink-features=AutomationControlled']
        )

        # Create or load context
        if STORAGE_STATE_PATH.exists():
            context = await browser.new_context(
                storage_state=str(STORAGE_STATE_PATH),
                viewport={'width': 1920, 'height': 1080}
            )
            print("✓ Loaded saved session")
        else:
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )

        page = await context.new_page()

        try:
            # Navigate to Google
            url = f"https://www.google.com/search?q={query}"
            await page.goto(url, wait_until="domcontentloaded")

            # Handle consent
            await handle_consent(page)

            # Check for CAPTCHA
            if await detect_captcha(page):
                print("❌ CAPTCHA detected - stopping")
                await page.screenshot(path="debug_captcha.png")
                return []

            # Parse results
            results = await parse_results(page, max_results)

            # Save session state
            await context.storage_state(path=str(STORAGE_STATE_PATH))

            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = "".join(c if c.isalnum() else "_" for c in query)[:50]
            output_file = RESULTS_DIR / f"{safe_query}_{timestamp}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "query": query,
                    "timestamp": timestamp,
                    "results_count": len(results),
                    "results": results
                }, f, indent=2, ensure_ascii=False)

            print(f"✓ Found {len(results)} results")
            print(f"✓ Saved to {output_file.name}")

            return results

        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path="debug_error.png")
            return []
        finally:
            await browser.close()


async def batch_search():
    """Run multiple searches with delay"""
    queries = [
        "site:python.org playwright tutorial",
        "playwright vs selenium 2024",
        "web scraping best practices",
        "asyncio python windows",
        "fastapi websocket example"
    ]

    all_results = {}

    for i, query in enumerate(queries):
        results = await search_google(query, max_results=5)
        all_results[query] = results

        # Delay between searches (except last)
        if i < len(queries) - 1:
            print(f"⏳ Waiting 3 seconds...")
            await asyncio.sleep(3)

    # Save combined results
    output_file = RESULTS_DIR / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Batch complete! Saved to {output_file.name}")
    return all_results


async def main():
    """Main entry point"""
    print("=== Playwright Google Search Test ===")

    # Single search
    await search_google("playwright python examples", max_results=3)

    # Wait before batch
    print("\n⏳ Waiting 5 seconds before batch...")
    await asyncio.sleep(5)

    # Batch search
    await batch_search()


if __name__ == "__main__":
    # Windows fix
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())