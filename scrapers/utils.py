"""
Shared fetch utility — routes requests through ScraperAPI when
SCRAPERAPI_KEY is set, otherwise falls back to direct requests.
"""

import os
import time
import random
import requests

SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url: str, render_js: bool = False, delay: bool = True) -> str | None:
    """
    Fetch a URL, routing through ScraperAPI if SCRAPERAPI_KEY is available.
    render_js=True uses ScraperAPI's JS rendering (costs 5 credits instead of 1).
    """
    if delay:
        time.sleep(random.uniform(1, 3))

    if SCRAPERAPI_KEY:
        params = {"api_key": SCRAPERAPI_KEY, "url": url}
        if render_js:
            params["render"] = "true"
        try:
            resp = requests.get(
                "https://api.scraperapi.com",
                params=params,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            print(f"    [ScraperAPI] error fetching {url[:60]}: {exc}")
            return None
    else:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            print(f"    [direct] error fetching {url[:60]}: {exc}")
            return None
