import json
import re

from bs4 import BeautifulSoup

from config import ZILLOW_AREAS
from scrapers.utils import fetch


def _extract_listings(data: dict) -> list:
    """Try multiple known __NEXT_DATA__ paths to find listing arrays."""
    candidate_paths = [
        ["props", "pageProps", "searchPageState", "cat1", "searchResults", "listResults"],
        ["props", "pageProps", "searchPageState", "cat2", "searchResults", "listResults"],
        ["props", "pageProps", "componentProps", "listResults"],
    ]
    for path in candidate_paths:
        node = data
        for key in path:
            if not isinstance(node, dict):
                break
            node = node.get(key)
        if isinstance(node, list) and node:
            return node
    return []


def _parse_html(html: str) -> list:
    soup = BeautifulSoup(html, "lxml")
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script or not script.string:
        return []
    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return []

    raw = _extract_listings(data)
    listings = []
    for item in raw:
        zpid = str(item.get("zpid") or item.get("id") or "")
        if not zpid:
            continue
        detail = item.get("detailUrl", "")
        listings.append(
            {
                "zpid":    zpid,
                "address": item.get("address", "N/A"),
                "price":   item.get("price", "N/A"),
                "beds":    item.get("beds", "N/A"),
                "baths":   item.get("baths", "N/A"),
                "sqft":    item.get("area", "N/A"),
                "url":     f"https://www.zillow.com{detail}" if detail else "",
                "status":  item.get("statusType", ""),
            }
        )
    return listings


def fetch_area(area_name: str, url: str) -> list:
    html = fetch(url)
    if not html:
        print(f"  [{area_name}] fetch failed")
        return []
    listings = _parse_html(html)
    print(f"  [{area_name}] {len(listings)} listings fetched")
    return listings


def get_all_listings() -> dict:
    """Return {area_name: [listing, ...]} for all configured areas."""
    result = {}
    for area, url in ZILLOW_AREAS.items():
        result[area] = fetch_area(area, url)
    return result


def diff_listings(old_state: dict, new_state: dict) -> tuple[list, list]:
    """
    Compare old and new states.
    Returns (new_listings, price_changes).
    Each item carries an extra 'area' key.
    """
    new_found = []
    price_changes = []

    for area, listings in new_state.items():
        old_by_id = {item["zpid"]: item for item in old_state.get(area, [])}
        for listing in listings:
            zpid = listing["zpid"]
            if zpid not in old_by_id:
                new_found.append({**listing, "area": area})
            else:
                old_price = old_by_id[zpid].get("price", "")
                new_price = listing.get("price", "")
                if old_price and new_price and old_price != new_price:
                    price_changes.append(
                        {**listing, "area": area, "old_price": old_price}
                    )

    return new_found, price_changes
