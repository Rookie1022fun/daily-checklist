import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Styling ───────────────────────────────────────────────────────────────────
STYLE = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f5f5f5; margin: 0; padding: 20px; color: #333; }
.container { max-width: 700px; margin: 0 auto; background: #fff;
             border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,.08); }
.header    { background: #1a1a2e; color: #fff; padding: 24px 30px; }
.header h1 { margin: 0; font-size: 22px; }
.header p  { margin: 4px 0 0; opacity: .7; font-size: 13px; }
.section   { padding: 20px 30px; border-bottom: 1px solid #eee; }
.section h2{ margin: 0 0 14px; font-size: 16px; color: #1a1a2e; }
.tag       { display: inline-block; padding: 2px 8px; border-radius: 12px;
             font-size: 11px; font-weight: 600; margin-bottom: 4px; }
.tag-new   { background: #d4edda; color: #155724; }
.tag-price { background: #fff3cd; color: #856404; }
.tag-amex  { background: #e3f2fd; color: #0d47a1; }
.tag-chase { background: #fce4ec; color: #880e4f; }
.card      { background: #f9f9f9; border-radius: 8px; padding: 12px 14px;
             margin-bottom: 10px; }
.card a    { color: #1a73e8; text-decoration: none; font-weight: 600; }
.card a:hover { text-decoration: underline; }
.meta      { font-size: 12px; color: #888; margin-top: 4px; }
.empty     { color: #aaa; font-style: italic; font-size: 14px; }
.footer    { padding: 14px 30px; font-size: 12px; color: #aaa; text-align: center; }
"""


def _listing_card(listing: dict, tag: str, label: str) -> str:
    price_line = listing.get("price", "N/A")
    if tag == "tag-price":
        price_line = (
            f'<s style="color:#aaa">{listing.get("old_price","")}</s>'
            f' &rarr; <strong>{listing.get("price","N/A")}</strong>'
        )
    return f"""
    <div class="card">
      <span class="tag {tag}">{label}</span>
      <div><a href="{listing.get('url','#')}">{listing.get('address','N/A')}</a></div>
      <div class="meta">
        {price_line} &nbsp;|&nbsp;
        {listing.get('beds','?')} bd / {listing.get('baths','?')} ba &nbsp;|&nbsp;
        {listing.get('sqft','?')} sqft &nbsp;|&nbsp;
        <em>{listing.get('area','')}</em>
      </div>
    </div>"""


def _card_news_card(item: dict, tag: str) -> str:
    return f"""
    <div class="card">
      <div><a href="{item.get('url','#')}">{item.get('title','')}</a></div>
      <div class="meta">{item.get('published','')} &nbsp;·&nbsp; Doctor of Credit</div>
    </div>"""


def build_html(date_str: str, new_listings: list, price_changes: list,
               card_updates: dict) -> str:
    # ── Zillow section ────────────────────────────────────────────────────────
    zillow_html = ""
    if not new_listings and not price_changes:
        zillow_html = '<p class="empty">今日无新房源或价格变动。</p>'
    else:
        for listing in new_listings:
            zillow_html += _listing_card(listing, "tag-new", "NEW")
        for listing in price_changes:
            zillow_html += _listing_card(listing, "tag-price", "价格变动")

    # ── Credit card sections ──────────────────────────────────────────────────
    amex_html = ""
    for item in card_updates.get("amex", []):
        amex_html += _card_news_card(item, "tag-amex")
    if not amex_html:
        amex_html = '<p class="empty">今日无 Amex 相关动态。</p>'

    chase_html = ""
    for item in card_updates.get("chase", []):
        chase_html += _card_news_card(item, "tag-chase")
    if not chase_html:
        chase_html = '<p class="empty">今日无 Chase 相关动态。</p>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{STYLE}</style></head>
<body><div class="container">
  <div class="header">
    <h1>每日信息速报</h1>
    <p>{date_str} &nbsp;·&nbsp; North San Jose &amp; Fremont 租房 + 信用卡福利</p>
  </div>

  <div class="section">
    <h2>🏠 Zillow 2B2B 租房更新</h2>
    {zillow_html}
  </div>

  <div class="section">
    <h2>💳 American Express 动态</h2>
    {amex_html}
  </div>

  <div class="section">
    <h2>💳 Chase 动态</h2>
    {chase_html}
  </div>

  <div class="footer">由 GitHub Actions 自动生成 · 数据来源: Zillow, Doctor of Credit</div>
</div></body></html>"""


def send_report(date_str: str, new_listings: list, price_changes: list,
                card_updates: dict) -> None:
    gmail_user  = os.environ["GMAIL_USER"]
    gmail_pass  = os.environ["GMAIL_APP_PASSWORD"]
    recipient   = os.environ["RECIPIENT_EMAIL"]

    html = build_html(date_str, new_listings, price_changes, card_updates)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"每日速报 {date_str} — 湾区租房 + 信用卡"
    msg["From"]    = gmail_user
    msg["To"]      = recipient
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.sendmail(gmail_user, recipient, msg.as_bytes())

    print(f"  [email] Sent to {recipient}")
