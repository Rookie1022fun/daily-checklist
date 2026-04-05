"""
Scrapers for specific apartment complexes:
  - River View Apartments (Irvine Company) — 250 Brandon St, San Jose
  - Vista 99 (Equity Residential)         — 99 Vista Montana, San Jose
Both complexes are in North San Jose. We filter for 2B/2BA units.
"""

import hashlib
import json
import re

from bs4 import BeautifulSoup

from scrapers.utils import fetch as _fetch_url


COMPLEXES = {
    "River View (Irvine Co.)": {
        "availability_url": (
            "https://www.irvinecompanyapartments.com"
            "/locations/northern-california/san-jose/river-view/availability.html"
        ),
        "home_url": (
            "https://www.irvinecompanyapartments.com"
            "/locations/northern-california/san-jose/river-view.html"
        ),
    },
    "Vista 99 (Equity)": {
        "availability_url": (
            "https://www.equityapartments.com"
            "/san-francisco-bay/north-san-jose/vista-99-apartments"
        ),
        "home_url": (
            "https://www.equityapartments.com"
            "/san-francisco-bay/north-san-jose/vista-99-apartments"
        ),
    },
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _fetch(url: str) -> str | None:
    return _fetch_url(url)


def _content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _is_2b2b(beds, baths) -> bool:
    """Loose check — accept '2', 2, '2 bed', '2BR', etc."""
    def norm(v):
        return str(v).strip().lower().replace("bed", "").replace("bath", "").replace("br", "").replace("ba", "").strip()
    try:
        b = float(norm(beds))
        a = float(norm(baths))
        return b == 2 and a >= 2
    except (ValueError, TypeError):
        return False


# ── Irvine Company parser ─────────────────────────────────────────────────────

def _parse_irvine(html: str) -> list[dict]:
    """
    Irvine Company embeds availability data in JSON-LD or a JS variable.
    We try multiple strategies.
    """
    units = []

    # Strategy 1: look for JSON-LD with apartment unit data
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") in ("ApartmentComplex", "Apartment"):
                    # might contain containsPlace or similar
                    pass
        except Exception:
            continue

    # Strategy 2: look for embedded JS object (e.g. window.__INITIAL_STATE__)
    for script in soup.find_all("script"):
        text = script.string or ""
        # Irvine Company sometimes embeds floorplan data as a JS array
        m = re.search(r"floorplans\s*[:=]\s*(\[.*?\])\s*[,;]", text, re.S)
        if m:
            try:
                plans = json.loads(m.group(1))
                for p in plans:
                    beds  = p.get("bedrooms") or p.get("beds") or p.get("bed")
                    baths = p.get("bathrooms") or p.get("baths") or p.get("bath")
                    price = p.get("price") or p.get("startingPrice") or p.get("minPrice")
                    if _is_2b2b(beds, baths):
                        units.append({
                            "name":  p.get("name") or p.get("floorplanName") or "2B/2BA",
                            "beds":  2, "baths": 2,
                            "price": str(price) if price else "N/A",
                            "sqft":  str(p.get("squareFeet") or p.get("sqft") or "N/A"),
                            "avail": str(p.get("availableDate") or p.get("availability") or ""),
                            "url":   COMPLEXES["River View (Irvine Co.)"]["availability_url"],
                        })
            except Exception:
                pass

    # Strategy 3: scrape visible DOM cards (fallback)
    if not units:
        cards = soup.select("[class*='floor'], [class*='unit'], [class*='plan']")
        for card in cards:
            text = card.get_text(" ", strip=True)
            bed_m  = re.search(r"(\d)\s*(?:bed|br)", text, re.I)
            bath_m = re.search(r"(\d(?:\.\d)?)\s*(?:bath|ba)", text, re.I)
            price_m = re.search(r"\$[\d,]+", text)
            if bed_m and bath_m and _is_2b2b(bed_m.group(1), bath_m.group(1)):
                units.append({
                    "name":  "2B/2BA",
                    "beds":  2, "baths": 2,
                    "price": price_m.group(0) if price_m else "N/A",
                    "sqft":  "N/A",
                    "avail": "",
                    "url":   COMPLEXES["River View (Irvine Co.)"]["availability_url"],
                })

    return units


# ── Equity Apartments parser ──────────────────────────────────────────────────

def _parse_equity(html: str) -> list[dict]:
    units = []
    soup = BeautifulSoup(html, "lxml")

    # Strategy 1: Equity often has JSON in a <script id="__NEXT_DATA__"> or similar
    for script in soup.find_all("script", {"id": "__NEXT_DATA__"}):
        try:
            data = json.loads(script.string or "")
            # flatten and search for unit arrays
            raw = json.dumps(data)
            # look for price patterns near "2 bed" context — rough extraction
            matches = re.findall(
                r'"(?:beds|bedrooms)"\s*:\s*2\b[^}]{0,300}"(?:price|rent|monthlyRent)"\s*:\s*(\d+)',
                raw, re.S
            )
            for price in matches:
                units.append({
                    "name": "2B/2BA", "beds": 2, "baths": 2,
                    "price": f"${int(price):,}", "sqft": "N/A", "avail": "",
                    "url": COMPLEXES["Vista 99 (Equity)"]["availability_url"],
                })
            if units:
                break
        except Exception:
            continue

    # Strategy 2: DOM scraping
    if not units:
        for card in soup.select("[class*='unit'], [class*='floor'], [class*='plan'], li[class*='apt']"):
            text = card.get_text(" ", strip=True)
            bed_m   = re.search(r"(\d)\s*(?:bed|br)", text, re.I)
            bath_m  = re.search(r"(\d(?:\.\d)?)\s*(?:bath|ba)", text, re.I)
            price_m = re.search(r"\$[\d,]+", text)
            if bed_m and bath_m and _is_2b2b(bed_m.group(1), bath_m.group(1)):
                units.append({
                    "name": "2B/2BA", "beds": 2, "baths": 2,
                    "price": price_m.group(0) if price_m else "N/A",
                    "sqft": "N/A", "avail": "",
                    "url": COMPLEXES["Vista 99 (Equity)"]["availability_url"],
                })

    return units


# ── public API ────────────────────────────────────────────────────────────────

_PARSERS = {
    "River View (Irvine Co.)": _parse_irvine,
    "Vista 99 (Equity)":       _parse_equity,
}


def get_complex_data() -> dict:
    """
    Returns {
        complex_name: {
            "units":        [unit_dict, ...],   # 2B/2BA units found
            "page_hash":    str,                # MD5 of raw page (change detection)
            "fetch_ok":     bool,
        }
    }
    """
    result = {}
    for name, cfg in COMPLEXES.items():
        html = _fetch(cfg["availability_url"])
        if not html:
            result[name] = {"units": [], "page_hash": "", "fetch_ok": False}
            continue

        parser = _PARSERS[name]
        units  = parser(html)
        phash  = _content_hash(html)
        result[name] = {"units": units, "page_hash": phash, "fetch_ok": True}
        print(f"  [{name}] {len(units)} 2B/2BA units parsed, hash={phash[:8]}")

    return result


def diff_complexes(old_state: dict, new_data: dict) -> dict:
    """
    Compares old vs new complex data.
    Returns {
        complex_name: {
            "page_changed": bool,
            "new_units":    [...],
            "gone_units":   [...],
            "price_changes":[...],
            "home_url":     str,
            "availability_url": str,
        }
    }
    """
    diffs = {}
    for name, new in new_data.items():
        old = old_state.get(name, {})
        page_changed = old.get("page_hash", "") != new.get("page_hash", "")

        old_units = {u["name"] + u.get("sqft", ""): u for u in old.get("units", [])}
        new_units = {u["name"] + u.get("sqft", ""): u for u in new.get("units", [])}

        new_found    = [u for k, u in new_units.items() if k not in old_units]
        gone         = [u for k, u in old_units.items() if k not in new_units]
        price_chgs   = [
            {**new_units[k], "old_price": old_units[k]["price"]}
            for k in new_units
            if k in old_units and old_units[k]["price"] != new_units[k]["price"]
        ]

        diffs[name] = {
            "page_changed":    page_changed,
            "new_units":       new_found,
            "gone_units":      gone,
            "price_changes":   price_chgs,
            "home_url":        COMPLEXES[name]["home_url"],
            "availability_url": COMPLEXES[name]["availability_url"],
            "fetch_ok":        new.get("fetch_ok", False),
        }

    return diffs
