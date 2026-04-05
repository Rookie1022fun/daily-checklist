from datetime import datetime, timedelta, timezone

import feedparser

from config import AMEX_KEYWORDS, CHASE_KEYWORDS, DOC_RSS_URL


def _matches(text: str, keywords: list) -> bool:
    t = text.lower()
    return any(kw in t for kw in keywords)


def get_card_updates(lookback_hours: int = 25) -> dict:
    """
    Pull Doctor of Credit RSS and return Amex/Chase items published
    within the last `lookback_hours` hours.
    Returns {"amex": [...], "chase": [...]}.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    try:
        feed = feedparser.parse(DOC_RSS_URL)
        entries = feed.entries
    except Exception as exc:
        print(f"  [credit_cards] RSS fetch error: {exc}")
        return {"amex": [], "chase": []}

    amex_updates  = []
    chase_updates = []

    for entry in entries:
        try:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            continue

        if published < cutoff:
            continue

        title   = entry.get("title", "")
        summary = entry.get("summary", "")
        full    = f"{title} {summary}"

        item = {
            "title":     title,
            "url":       entry.get("link", ""),
            "published": published.strftime("%Y-%m-%d %H:%M UTC"),
            "summary":   summary[:300],
        }

        if _matches(full, AMEX_KEYWORDS):
            amex_updates.append(item)
        if _matches(full, CHASE_KEYWORDS):
            chase_updates.append(item)

    print(f"  [credit_cards] Amex: {len(amex_updates)}, Chase: {len(chase_updates)}")
    return {"amex": amex_updates, "chase": chase_updates}
