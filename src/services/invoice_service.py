"""
Invoice/Receipt generation service.

Generates a printable HTML invoice and, when available, a PDF using headless Chromium (Playwright).
Falls back to returning HTML if PDF generation is not available at runtime.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Optional
from src.utils.i18n import i18n

logger = logging.getLogger(__name__)


def _build_invoice_html(order: Dict, business: Dict | None = None, receipt_width_mm: Optional[int] = None, user_id: Optional[int] = None) -> str:
    """Build minimal, RTL-aware HTML for invoice/receipt.

    If receipt_width_mm is provided (e.g., 58), generate a narrow layout suitable for thermal printers.
    """
    biz_name = (business or {}).get("business_name", "Samna Salta")
    biz_desc = (business or {}).get("business_description", "")
    address = order.get("delivery_address")
    instructions = order.get("delivery_instructions")
    created_at = order.get("created_at")
    if isinstance(created_at, datetime):
        created_at_str = created_at.strftime("%Y-%m-%d %H:%M")
    else:
        created_at_str = str(created_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M"))

    width_css = f"@page {{ size: {receipt_width_mm}mm auto; margin: 6mm; }} body {{ width: {receipt_width_mm}mm; }}" if receipt_width_mm else "@page { size: A4; margin: 15mm; }"

    # Localized labels
    L = lambda k: i18n.get_text(k, user_id=user_id)

    items_html = []
    for idx, item in enumerate(order.get("items", []), start=1):
        name = item.get("product_name", "")
        # Strip emojis for invoice aesthetics
        try:
            import re
            name = re.sub(r"[\U00010000-\U0010ffff]", "", name)
        except Exception:
            pass
        qty = item.get("quantity", 1)
        unit = item.get("unit_price", 0)
        total = item.get("total_price", unit * qty)
        items_html.append(f"<tr><td>{idx}. {name}</td><td class='c'>{qty}</td><td class='r'>₪{unit:.2f}</td><td class='r'>₪{total:.2f}</td></tr>")

    delivery_charge = float(order.get("delivery_charge") or 0)
    # Compute subtotal as sum of item totals
    try:
        subtotal = sum(float(it.get("total_price", float(it.get("unit_price", 0)) * int(it.get("quantity", 1)))) for it in order.get("items", []))
    except Exception:
        subtotal = float(order.get("subtotal") or 0)
    total = subtotal + delivery_charge

    delivery_block = ""
    if (order.get("delivery_method") or "").lower() == "delivery":
        if address:
            delivery_block += f"<div><strong>Address:</strong> {address}</div>"
        if instructions:
            delivery_block += f"<div><strong>Delivery Instructions:</strong> {instructions}</div>"

    html = f"""
<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8" />
  <style>
    {width_css}
    body {{ font-family: Arial, Helvetica, sans-serif; color: #111; }}
    h1, h2, h3 {{ margin: 0 0 8px; }}
    .header {{ border-bottom: 1px solid #ddd; padding-bottom: 8px; margin-bottom: 12px; }}
    .meta {{ font-size: 12px; color: #555; margin-bottom: 12px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ padding: 6px 4px; border-bottom: 1px solid #eee; }}
    tfoot td {{ border-top: 1px solid #ccc; font-weight: bold; }}
    .r {{ text-align: right; }}
    .c {{ text-align: center; }}
  </style>
  <title>{L('INVOICE_TITLE').format(id=order.get('order_id', order.get('order_number','')))}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta name="color-scheme" content="light dark" />
  <meta name="supported-color-schemes" content="light dark" />
  <meta name="format-detection" content="telephone=no" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:;" />
  <style>@media print {{ .no-print {{ display: none !important; }} }}</style>
  <style>html, body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}</style>
  <style>/* basic rtl support */ body {{ direction: rtl; }}</style>
</head>
<body>
  <div class="header">
    <h1>{biz_name}</h1>
    <div class="meta">{biz_desc}</div>
    <div class="meta">{L('INVOICE_TITLE').format(id=order.get('order_id', order.get('order_number','')))} • {created_at_str}</div>
  </div>

  <div class="meta">
    <div><strong>{L('INVOICE_CUSTOMER')}:</strong> {order.get('customer_name','')}</div>
    <div><strong>{L('INVOICE_PHONE')}:</strong> {order.get('customer_phone','')}</div>
    <div><strong>{L('INVOICE_METHOD')}:</strong> {(order.get('delivery_method') or '').title()}</div>
    {delivery_block}
  </div>

  <table>
    <thead>
      <tr><th>{L('INVOICE_ITEM')}</th><th class='c'>{L('INVOICE_QTY')}</th><th class='r'>{L('INVOICE_UNIT')}</th><th class='r'>{L('INVOICE_TOTAL')}</th></tr>
    </thead>
    <tbody>
      {''.join(items_html)}
    </tbody>
    <tfoot>
      <tr><td colspan="3">{L('INVOICE_SUBTOTAL')}</td><td class='r'>₪{subtotal:.2f}</td></tr>
      <tr><td colspan="3">{L('INVOICE_DELIVERY')}</td><td class='r'>₪{delivery_charge:.2f}</td></tr>
      <tr><td colspan="3">{L('INVOICE_GRAND_TOTAL')}</td><td class='r'>₪{total:.2f}</td></tr>
    </tfoot>
  </table>
</body>
</html>
"""
    return html


async def generate_pdf_from_html(html: str) -> Optional[bytes]:
    """Generate a PDF from HTML using Playwright Chromium, if available.
    Returns PDF bytes or None on failure.
    """
    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        logger.warning("Playwright not available for PDF generation: %s", e)
        return None

    async def _render() -> Optional[bytes]:
        async with async_playwright() as p:
            # Launch with flags that are friendly to containers like Render/Heroku
            browser = await p.chromium.launch(
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            page = await browser.new_page()
            await page.set_content(html, wait_until="load")
            pdf_bytes = await page.pdf(format="A4", print_background=True)
            await browser.close()
            return pdf_bytes
    try:
        return await _render()
    except Exception as e:
        # Attempt one-time browser install at runtime, then retry
        logger.error("Failed to render PDF via Playwright: %s", e)
        try:
            import subprocess, sys
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
            return await _render()
        except Exception as e2:
            logger.error("PDF retry after install failed: %s", e2)
            return None


async def warmup_playwright_chromium() -> None:
    """Warm up Playwright by ensuring Chromium is installed and can launch.

    Called at service startup to avoid slow first invoice and repeated taps.
    Safe to run multiple times.
    """
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except Exception as e:
        logger.info("Playwright not installed; skipping warm-up: %s", e)
        return

    # Heuristic: if cache dir lacks chromium, perform install
    try:
        cache_dir = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "/opt/render/.cache/ms-playwright"
        needs_install = not os.path.isdir(cache_dir) or not any(
            name.startswith("chromium") for name in os.listdir(cache_dir)
        )
    except Exception:
        needs_install = True

    if needs_install:
        try:
            import subprocess, sys
            logger.info("Playwright warm-up: installing chromium...")
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
        except Exception as e:
            logger.warning("Playwright warm-up install failed: %s", e)
            return

    # Verify we can launch a browser
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])  # type: ignore
            await browser.close()
        logger.info("Playwright warm-up completed")
    except Exception as e:
        logger.warning("Playwright warm-up verification failed: %s", e)


async def build_invoice_pdf(order: Dict, business: Dict | None = None, receipt: bool = False, user_id: Optional[int] = None) -> Dict[str, Optional[bytes]]:
    """Build invoice or receipt PDF (and always return the HTML too for fallback).

    Returns dict: {"pdf": bytes|None, "html": str}
    """
    html = _build_invoice_html(order, business, receipt_width_mm=58 if receipt else None, user_id=user_id)
    pdf = await generate_pdf_from_html(html)
    return {"pdf": pdf, "html": html}


