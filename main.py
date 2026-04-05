"""
Daily checklist runner.
  1. Load previous Zillow state from data/zillow_state.json
  2. Fetch current Zillow listings
  3. Diff → new listings + price changes
  4. Fetch credit card news from DoC RSS
  5. Send HTML email
  6. Save new state back to data/zillow_state.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from email_sender import send_report
from scrapers.credit_cards import get_card_updates
from scrapers.zillow import diff_listings, get_all_listings

STATE_FILE = Path(__file__).parent / "data" / "zillow_state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def main() -> None:
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    print(f"=== Daily checklist {date_str} ===")

    # ── Zillow ────────────────────────────────────────────────────────────────
    print("\n[1/3] Fetching Zillow listings...")
    old_state   = load_state()
    new_state   = get_all_listings()
    new_listings, price_changes = diff_listings(old_state, new_state)
    print(f"  New listings: {len(new_listings)}, Price changes: {len(price_changes)}")

    # ── Credit cards ──────────────────────────────────────────────────────────
    print("\n[2/3] Fetching credit card updates...")
    card_updates = get_card_updates()

    # ── Email ─────────────────────────────────────────────────────────────────
    print("\n[3/3] Sending email...")
    try:
        send_report(date_str, new_listings, price_changes, card_updates)
    except KeyError as exc:
        print(f"  [email] Missing env var: {exc}")
        print("  Set GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL and retry.")
        sys.exit(1)

    # ── Persist state ─────────────────────────────────────────────────────────
    save_state(new_state)
    print("\nDone. State saved.")


if __name__ == "__main__":
    main()
