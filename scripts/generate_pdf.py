"""
generate_pdf.py
Loads the BCOM COT Analyzer HTML page in a headless Chromium browser,
waits for all charts to render, then exports to PDF.

Requirements: playwright (pip install playwright && playwright install chromium)
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

# ── Config ─────────────────────────────────────────────────────────────────
# Path to your index.html (relative to repo root)
HTML_FILE = Path(__file__).parent.parent / "index.html"
OUTPUT_PDF = Path(__file__).parent.parent / "cot_report.pdf"

# The commodity to pre-select (must match the 'value' attribute in the dropdown)
# Use the CFTC API name as it appears in the dropdown value
DEFAULT_COMMODITY = "COTTON NO. 2 - ICE FUTURES U.S."

# How long to wait (ms) after page load for all CFTC API calls to complete
# CFTC API can be slow — 90 seconds is a safe buffer for all 23 commodities
API_WAIT_MS = 90_000

# ── PDF page settings ──────────────────────────────────────────────────────
PDF_OPTIONS = {
    "format": "A4",
    "landscape": True,
    "print_background": True,
    "margin": {
        "top": "8mm",
        "bottom": "8mm",
        "left": "10mm",
        "right": "10mm",
    },
}


async def generate():
    et = timezone(timedelta(hours=-5))  # EST (use -4 for EDT)
    now_et = datetime.now(et)
    date_str = now_et.strftime("%Y-%m-%d")
    print(f"[COT PDF] Starting generation for report week: {date_str}")

    if not HTML_FILE.exists():
        print(f"ERROR: HTML file not found at {HTML_FILE}")
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        # Navigate to the local HTML file
        file_url = HTML_FILE.resolve().as_uri()
        print(f"[COT PDF] Loading: {file_url}")
        await page.goto(file_url, wait_until="networkidle", timeout=30_000)

        # ── FIX: Wait for dropdown to be populated with actual options ─────────
        # The dropdown starts with just "-- Loading..." and gets filled via JS
        # We need to wait until real options exist [^8^][^12^][^13^]
        print("[COT PDF] Waiting for commodity list to populate...")
        await page.wait_for_function(
            "() => {"
            "  const sel = document.getElementById('commoditySelect');"
            "  if (!sel) return false;"
            "  // Check if we have options beyond the placeholder"
            "  const opts = sel.querySelectorAll('option[value]');"
            "  return opts.length > 1 && opts[0].value !== '';"
            "}",
            timeout=20_000,
        )
        
        # ── FIX: Wait for the specific commodity option to exist ───────────────
        # This ensures the API has returned data for our target commodity [^4^][^6^]
        print(f"[COT PDF] Waiting for option: {DEFAULT_COMMODITY}...")
        await page.wait_for_selector(
            f'#commoditySelect option[value="{DEFAULT_COMMODITY}"]',
            timeout=20_000,
        )
        print("[COT PDF] Commodity list loaded.")

        # ── FIX: Select by value (more reliable than label for dynamic dropdowns) ─
        # Use the exact CFTC API name as the value [^8^]
        await page.select_option("#commoditySelect", DEFAULT_COMMODITY)
        await page.wait_for_timeout(500)
        print(f"[COT PDF] Selected commodity: {DEFAULT_COMMODITY}")

        # Click Generate Charts — this auto-triggers all sections
        await page.click("#fetchBtn")
        print(f"[COT PDF] Clicked Generate Charts. Waiting up to {API_WAIT_MS/1000:.0f}s for all data...")

        # Wait for the loading spinner to disappear
        await page.wait_for_function(
            "document.getElementById('loading').style.display === 'none' || "
            "document.getElementById('loading').style.display === ''",
            timeout=API_WAIT_MS,
        )

        # Extra wait to ensure all async sections (scatter, summary) finished rendering
        await page.wait_for_timeout(5_000)
        print("[COT PDF] All sections rendered. Generating PDF...")

        # Export PDF
        pdf_bytes = await page.pdf(**PDF_OPTIONS)
        OUTPUT_PDF.write_bytes(pdf_bytes)
        print(f"[COT PDF] PDF saved to: {OUTPUT_PDF} ({len(pdf_bytes)/1024:.1f} KB)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(generate())
