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

        # ── FIX: Wait for the specific commodity option to exist ───────────────
        # The dropdown is populated dynamically via JavaScript.
        # We must wait for the specific option to be added to the DOM [^1^][^4^][^29^]
        print(f"[COT PDF] Waiting for commodity option: {DEFAULT_COMMODITY}...")
        
        # Wait for the specific option to exist in the dropdown
        option_selector = f'#commoditySelect option[value="{DEFAULT_COMMODITY}"]'
        
        try:
            await page.wait_for_selector(
                option_selector,
                state="attached",  # Wait for element to be in DOM [^4^]
                timeout=30_000,
            )
            print("[COT PDF] Commodity option found.")
        except Exception as e:
            print(f"[COT PDF] Warning: Could not find exact option. Error: {e}")
            # Fallback: wait for any option with "Cotton" in the text
            await page.wait_for_selector(
                '#commoditySelect option:has-text("Cotton")',
                state="attached",
                timeout=10_000,
            )
            print("[COT PDF] Found Cotton option (fallback).")

        # ── FIX: Select by value (more reliable than label for dynamic dropdowns) ─
        # Use the exact CFTC API name as the value [^1^][^8^]
        try:
            await page.select_option("#commoditySelect", DEFAULT_COMMODITY)
            print(f"[COT PDF] Selected commodity: {DEFAULT_COMMODITY}")
        except Exception as e:
            print(f"[COT PDF] Error selecting by value: {e}")
            # Fallback: select by label text
            await page.select_option("#commoditySelect", label="Cotton (CT)")
            print("[COT PDF] Selected Cotton by label (fallback).")
        
        await page.wait_for_timeout(500)

        # Click Generate Charts — this auto-triggers all sections
        await page.click("#fetchBtn")
        print(f"[COT PDF] Clicked Generate Charts. Waiting up to {API_WAIT_MS/1000:.0f}s for all data...")

        # Wait for the loading spinner to disappear
        await page.wait_for_function(
            "() => document.getElementById('loading').style.display === 'none' || document.getElementById('loading').style.display === ''",
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
