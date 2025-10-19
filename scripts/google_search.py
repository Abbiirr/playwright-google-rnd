#!/usr/bin/env python3
"""
google_cli_scraper.py
Single-file, modular Playwright scraper with optional Google login.

Requirements:
  pip install playwright==1.* rich
  playwright install chromium

Examples:
  # Reuse/create a persistent profile, headless, and scrape 10 results
  python google_cli_scraper.py --query "site:playwright.dev launch_persistent_context" \
      --profile-name my_profile --headless --max-results 10

  # Do an INTERACTIVE login (opens a visible browser), then scrape
  GOOGLE_EMAIL="user@gmail.com" GOOGLE_PASSWORD="app-password" \
  python google_cli_scraper.py --query "Bangladesh fintech news" \
      --profile-name bank_ops --login --no-headless --slowmo 200

  # Save results to a file
  python google_cli_scraper.py -q "pixijs webgpu" -o results.json
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import re
from urllib.parse import urlparse, quote_plus

from playwright.async_api import async_playwright

# ---------- Logging ----------
def setup_logging(verbosity: int) -> None:
    level = logging.WARNING if verbosity == 0 else logging.INFO if verbosity == 1 else logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

log = logging.getLogger("google_cli_scraper")

# ---------- Files & Profiles ----------
def ensure_profile_dir(base: Path, name: str) -> Path:
    path = base / name
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_json(obj: Dict[str, Any], out_path: Optional[str]) -> None:
    if not out_path:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        return
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    log.info("Saved %s", out_path)

# ---------- Browser ----------
async def launch_context(p, profile_path: Path, headless: bool, slowmo: int):
    """
    Use a persistent context so cookies/sessions are reused across runs.
    """
    # Playwright doc: browser_type.launch_persistent_context(user_data_dir, **kwargs)
    # https://playwright.dev/python/docs/api/class-browsertype
    context = await p.chromium.launch_persistent_context(
        user_data_dir=str(profile_path),
        headless=headless,
        slow_mo=slowmo,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = await context.new_page()
    return context, page

# ---------- Google Login (optional) ----------
async def google_login(page, email: str, password: str, interactive_wait: bool = True):
    """
    Best-effort login flow. If 2FA is enabled, keep the browser VISIBLE and
    complete it manually, then press Enter in the terminal to continue.
    """
    log.info("Starting Google login flow...")
    await page.goto("https://accounts.google.com/signin/v2/identifier?hl=en")
    await page.wait_for_selector('input[type="email"]', timeout=60000)
    await page.fill('input[type="email"]', email)
    await page.click('#identifierNext')

    # Wait for password page
    await page.wait_for_selector('input[type="password"]', timeout=60000)
    await page.fill('input[type="password"]', password)
    await page.click('#passwordNext')

    # Either we land on an account page or encounter challenges (2FA/CAPTCHA)
    # Let the user resolve anything interactive.
    if interactive_wait:
        log.warning("If 2FA or a challenge appears, complete it in the browser window.")
        log.warning("Press Enter here when the account appears logged in...")
        try:
            input()
        except EOFError:
            pass

    # Try to confirm login by visiting google.com
    await page.goto("https://www.google.com")
    await page.wait_for_timeout(1500)
    log.info("Login step finished (cannot guarantee success if challenges persist).")
async def accept_consent(page) -> None:
    """Handle both google.com and consent.google.com variants."""
    # If we land on consent.google.com, wait for buttons
    if "consent.google" in page.url:
        try:
            # Try common “Accept all”/“I agree” labels via ARIA role
            btn = page.get_by_role("button", name=re.compile(r"(Accept|I agree|Agree)", re.I))
            if await btn.count():
                await btn.first.click()
                await page.wait_for_load_state("domcontentloaded")
        except Exception:
            pass
    else:
        # In-page banner on google.com (region-specific)
        try:
            btn = page.locator('button:has-text("I agree"), button:has-text("Accept all"), #L2AGLb')
            if await btn.count():
                await btn.first.click()
                await page.wait_for_timeout(400)
        except Exception:
            pass
# ---------- Scraping ----------
async def scrape_search(page, query: str, max_results: int = 10) -> Dict[str, Any]:
    # Use stable params to reduce layout variance
    home = "https://www.google.com/?hl=en&gl=us&pws=0"
    await page.goto(home)
    await page.wait_for_load_state("domcontentloaded")  # safer than arbitrary sleeps :contentReference[oaicite:2]{index=2}
    await accept_consent(page)

    # Type on the homepage; if it fails, fall back to direct /search URL
    try:
        box = page.locator('input[name="q"]')
        await box.click()
        await box.fill(query)
        await page.keyboard.press("Enter")
        await page.wait_for_selector("div#search", timeout=15000)
    except Exception:
        # Fallback: navigate straight to the results page
        search_url = f"https://www.google.com/search?hl=en&gl=us&pws=0&num={max_results}&q={quote_plus(query)}"
        await page.goto(search_url)
        await page.wait_for_load_state("domcontentloaded")
        await accept_consent(page)
        await page.wait_for_selector("div#search", timeout=30000)

    # Prefer robust selector: links that have an H3 (title)
    link_results = page.locator('div#search a:has(h3)')  # using :has() locator pattern :contentReference[oaicite:3]{index=3}
    count = await link_results.count()
    items: List[Dict[str, Any]] = []

    for i in range(min(count, max_results)):
        try:
            link = link_results.nth(i)
            href = await link.get_attribute("href")
            title = await link.locator("h3").inner_text()
            if not (href and title.strip()):
                continue
            # Optional snippet: best-effort nearby text
            snippet_el = link.locator("xpath=ancestor::div[contains(@class,'g')][1]//*[contains(@class,'VwiC3b') or @data-sncf='1']").first
            snippet = (await snippet_el.inner_text()) if await snippet_el.count() else None

            items.append({
                "position": len(items) + 1,
                "title": title.strip(),
                "link": href,
                "domain": urlparse(href).netloc,
                "snippet": snippet.strip() if snippet else None
            })
        except Exception as e:
            log.debug("skip result %d: %s", i + 1, e)

    return {
        "query": query,
        "timestamp": datetime.utcnow().isoformat(),
        "search_url": page.url,
        "results_count": len(items),
        "results": items
    }
# ---------- CLI ----------
def build_arg_parser() -> argparse.ArgumentParser:
    # argparse docs: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser(
        description="Playwright-based Google scraper with optional login (persistent profile)."
    )
    parser.add_argument("-q", "--query", required=True, help="Search query.")
    parser.add_argument("--max-results", type=int, default=10, help="Max results to capture.")
    parser.add_argument("--profile-name", default="google_profile", help="Profile directory name.")
    parser.add_argument("--profiles-dir", default="browser_profiles", help="Profiles root directory.")
    parser.add_argument("--slowmo", type=int, default=0, help="Playwright slow_mo in ms.")
    parser.add_argument("--headless", dest="headless", action="store_true", help="Run headless.")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run headed (visible).")
    parser.set_defaults(headless=True)

    # Optional login
    parser.add_argument("--login", action="store_true", help="Attempt Google login before scraping.")
    parser.add_argument("--email", default=os.getenv("GOOGLE_EMAIL"), help="Google email (or set GOOGLE_EMAIL).")
    parser.add_argument("--password", default=os.getenv("GOOGLE_PASSWORD"), help="Google password/app password (or set GOOGLE_PASSWORD).")

    # Output + verbosity
    parser.add_argument("-o", "--out", help="Path to write JSON results (default: print to stdout).")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="-v for INFO, -vv for DEBUG.")
    return parser

async def run(args):
    setup_logging(args.verbose)

    # Basic safety checks for login flow
    if args.login:
        if args.headless:
            log.warning("Login works best with a VISIBLE browser. Consider adding --no-headless.")
        if not args.email or not args.password:
            log.error("Login requested but no email/password supplied (via flags or env).")
            sys.exit(2)

    profiles_root = Path(args.profiles_dir)
    profile_path = ensure_profile_dir(profiles_root, args.profile_name)

    # Windows note: If you’re on Windows, Playwright handles event loop differences internally.
    async with async_playwright() as p:
        context, page = await launch_context(
            p, profile_path=profile_path, headless=args.headless, slowmo=args.slowmo
        )

        try:
            if args.login:
                await google_login(page, args.email, args.password, interactive_wait=not args.headless)
                # Save state for reuse
                state_file = profile_path / "state.json"
                await context.storage_state(path=str(state_file))
                log.info("Saved browser storage state to %s", state_file)

            data = await scrape_search(page, args.query, args.max_results)
            save_json(data, args.out)
        finally:
            await context.close()

def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        log.exception("Fatal error: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    main()

# CLI arguments (name → suggested value) — adjust as needed
# --query            → "pixijs webgpu"                  # REQUIRED search string
# --max-results      → 10                               # 10–25 typical
# --profiles-dir     → "./browser_profiles"             # root folder for profiles
# --profile-name     → "acct_1"                         # per-account/profile name
# --headless         → (present by default)             # omit when you want headless
# --no-headless      → (use this for first-time login)  # switch ON for interactive login/debug
# --slowmo           → 0                                # 100–250 ms when debugging/observing
# --login            → (add only when logging in)       # otherwise reuse saved session
# --email            → "you@gmail.com"                  # only with --login (or set env GOOGLE_EMAIL)
# --password         → "app-password"                   # only with --login (or set env GOOGLE_PASSWORD)
# --out              → "results.json"                   # omit to print to stdout
# -v / -vv           → -v (INFO) or -vv (DEBUG)         # verbosity level
