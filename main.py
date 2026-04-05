"""
Daily checklist runner.
  1. Fetch Zillow 2B/2BA listings (North SJ + Fremont) — new + price changes
  2. Fetch River View & Vista 99 official pages — unit availability + page changes
  3. Fetch Amex/Chase card news from Doctor of Credit RSS
  4. Send HTML email
  5. Persist state to data/ (committed back to git by GitHub Actions)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from email_sender import send_report
from scrapers.apartments import diff_complexes, get_complex_data
from scrapers.credit_cards import get_card_updates
from scrapers.zillow import diff_listings, get_all_listings

DATA_DIR          = Path(__file__).parent / "data"
ZILLOW_STATE_FILE = DATA_DIR / "zillow_state.json"
APT_STATE_FILE    = DATA_DIR / "apartments_state.json"


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    print(f"=== Daily checklist {date_str} ===")

    # ── 1. Zillow broad search ────────────────────────────────────────────────
    print("\n[1/4] Zillow area search...")
    old_zillow  = _load(ZILLOW_STATE_FILE)
    new_zillow  = get_all_listings()
    new_listings, price_changes = diff_listings(old_zillow, new_zillow)
    print(f"  New: {len(new_listings)}, Price changes: {len(price_changes)}")

    # ── 2. Specific complexes (River View + Vista 99) ─────────────────────────
    print("\n[2/4] Specific complex pages...")
    old_apts  = _load(APT_STATE_FILE)
    new_apts  = get_complex_data()
    apt_diffs = diff_complexes(old_apts, new_apts)

    # ── 3. Credit card news ───────────────────────────────────────────────────
    print("\n[3/4] Credit card RSS...")
    card_updates = get_card_updates()

    # ── 4. Email ──────────────────────────────────────────────────────────────
    print("\n[4/4] Sending email...")
    try:
        send_report(date_str, new_listings, price_changes, apt_diffs, card_updates)
    except KeyError as exc:
        print(f"  [email] Missing env var: {exc}")
        print("  Set GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL and retry.")
        sys.exit(1)

    # ── Persist ───────────────────────────────────────────────────────────────
    _save(ZILLOW_STATE_FILE, new_zillow)
    _save(APT_STATE_FILE, new_apts)
    print("\nDone. State saved.")


if __name__ == "__main__":
    main()
