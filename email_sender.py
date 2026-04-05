import os
import urllib.request
import urllib.error
import json

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
.tag-gone  { background: #f8d7da; color: #721c24; }
.tag-alert { background: #ffe0b2; color: #7b3f00; }
.tag-amex  { background: #e3f2fd; color: #0d47a1; }
.tag-chase { background: #fce4ec; color: #880e4f; }
.card      { background: #f9f9f9; border-radius: 8px; padding: 12px 14px;
             margin-bottom: 10px; }
.card a    { color: #1a73e8; text-decoration: none; font-weight: 600; }
.card a:hover { text-decoration: underline; }
.meta      { font-size: 12px; color: #888; margin-top: 4px; }
.empty     { color: #aaa; font-style: italic; font-size: 14px; }
.footer    { padding: 14px 30px; font-size: 12px; color: #aaa; text-align: center; }
.alert-bar { background: #fff3cd; border-left: 4px solid #ffc107;
             padding: 8px 12px; margin-bottom: 10px; border-radius: 4px;
             font-size: 13px; }
"""


# ── Zillow cards ──────────────────────────────────────────────────────────────

def _zillow_card(listing: dict, tag: str, label: str) -> str:
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


# ── Specific complex section ──────────────────────────────────────────────────

def _unit_row(unit: dict, tag: str, label: str) -> str:
    price = unit.get("price", "N/A")
    old_p = unit.get("old_price", "")
    price_html = (
        f'<s style="color:#aaa">{old_p}</s> &rarr; <strong>{price}</strong>'
        if old_p else f"<strong>{price}</strong>"
    )
    avail = unit.get("avail", "")
    return f"""
    <div class="card">
      <span class="tag {tag}">{label}</span>
      <div>{unit.get('name','2B/2BA')} &nbsp;·&nbsp; {price_html}
        {'&nbsp;·&nbsp; ' + unit.get('sqft','') + ' sqft' if unit.get('sqft','N/A') != 'N/A' else ''}
        {'&nbsp;·&nbsp; 可入住: ' + avail if avail else ''}
      </div>
    </div>"""


def _complex_section(name: str, diff: dict) -> str:
    home_url  = diff.get("home_url", "#")
    avail_url = diff.get("availability_url", "#")
    fetch_ok  = diff.get("fetch_ok", True)
    html      = f'<h3 style="margin:0 0 10px;font-size:14px"><a href="{home_url}">{name}</a></h3>'

    if not fetch_ok:
        html += f'<div class="alert-bar">⚠️ 今日页面抓取失败（服务器拦截），请手动查看：<a href="{avail_url}">点击直达房源页</a></div>'
        return html

    new_u  = diff.get("new_units", [])
    gone_u = diff.get("gone_units", [])
    chgs   = diff.get("price_changes", [])
    changed = diff.get("page_changed", False)

    if not new_u and not gone_u and not chgs:
        if changed:
            html += f'<div class="alert-bar">⚠️ 页面内容有变化，但未能解析出具体单元信息。' \
                    f' <a href="{avail_url}">手动查看</a></div>'
        else:
            html += '<p class="empty">今日无变动。</p>'
        return html

    for u in new_u:
        html += _unit_row(u, "tag-new", "NEW")
    for u in chgs:
        html += _unit_row(u, "tag-price", "价格变动")
    for u in gone_u:
        html += _unit_row(u, "tag-gone", "已下架")

    return html


# ── Credit card cards ─────────────────────────────────────────────────────────

def _cc_card(item: dict) -> str:
    return f"""
    <div class="card">
      <div><a href="{item.get('url','#')}">{item.get('title','')}</a></div>
      <div class="meta">{item.get('published','')} &nbsp;·&nbsp; Doctor of Credit</div>
    </div>"""


# ── Main builder ──────────────────────────────────────────────────────────────

def build_html(date_str: str, new_listings: list, price_changes: list,
               apt_diffs: dict, card_updates: dict) -> str:

    # Zillow
    zillow_html = ""
    if not new_listings and not price_changes:
        zillow_html = (
            '<p class="empty">今日无新房源或价格变动（或抓取被拦截）。</p>'
            '<div style="font-size:13px;margin-top:6px">'
            '直接搜索：'
            '<a href="https://www.zillow.com/north-san-jose-san-jose-ca/rentals/2-_beds/2.0-_baths/">North San Jose</a>'
            ' &nbsp;|&nbsp; '
            '<a href="https://www.zillow.com/fremont-ca/rentals/2-_beds/2.0-_baths/">Fremont</a>'
            '</div>'
        )
    else:
        for l in new_listings:
            zillow_html += _zillow_card(l, "tag-new", "NEW")
        for l in price_changes:
            zillow_html += _zillow_card(l, "tag-price", "价格变动")

    # Specific complexes — always show direct links even if scraping failed
    COMPLEX_LINKS = {
        "River View (Irvine Co.)": "https://www.irvinecompanyapartments.com/locations/northern-california/san-jose/river-view/availability.html",
        "Vista 99 (Equity)":       "https://www.equityapartments.com/san-francisco-bay/north-san-jose/vista-99-apartments",
    }
    complex_html = ""
    for name, diff in apt_diffs.items():
        link = COMPLEX_LINKS.get(name, "#")
        complex_html += f'<div style="margin-bottom:20px">{_complex_section(name, diff)}</div>'
    if not apt_diffs:
        for name, link in COMPLEX_LINKS.items():
            complex_html += f'<div style="margin-bottom:10px"><a href="{link}">{name} — 点击查看房源</a></div>'

    # Credit cards
    amex_html = "".join(_cc_card(i) for i in card_updates.get("amex", []))
    if not amex_html:
        amex_html = '<p class="empty">今日无 Amex 相关动态。</p>'

    chase_html = "".join(_cc_card(i) for i in card_updates.get("chase", []))
    if not chase_html:
        chase_html = '<p class="empty">今日无 Chase 相关动态。</p>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{STYLE}</style></head>
<body><div class="container">
  <div class="header">
    <h1>每日信息速报</h1>
    <p>{date_str} &nbsp;·&nbsp; North San Jose 重点公寓 + 湾区租房 + 信用卡福利</p>
  </div>

  <div class="section">
    <h2>🏠 重点公寓：River View &amp; Vista 99</h2>
    {complex_html}
  </div>

  <div class="section">
    <h2>🔍 Zillow 2B2B 周边新房源</h2>
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

  <div class="footer">由 GitHub Actions 自动生成 · 数据来源: Irvine Company, Equity Apartments, Zillow, Doctor of Credit</div>
</div></body></html>"""


def send_report(date_str: str, new_listings: list, price_changes: list,
                apt_diffs: dict, card_updates: dict) -> None:
    api_key   = os.environ["RESEND_API_KEY"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    html = build_html(date_str, new_listings, price_changes, apt_diffs, card_updates)

    payload = json.dumps({
        "from":    "Daily Checklist <onboarding@resend.dev>",
        "to":      [recipient],
        "subject": f"每日速报 {date_str} — 湾区租房 + 信用卡",
        "html":    html,
    }).encode()

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    print(f"  [email] Sent, id={result.get('id')} → {recipient}")
