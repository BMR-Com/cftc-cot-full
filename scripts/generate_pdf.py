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
    "prefer_css_page_size": True,  # Respect @page CSS rules from HTML
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
        
        # Use networkidle to wait for initial page load including JS execution
        await page.goto(file_url, wait_until="networkidle", timeout=30_000)

        # ── Wait for dropdown to be populated with actual options ─────────
        print("[COT PDF] Waiting for commodity list to populate...")
        
        option_selector = f'#commoditySelect option[value="{DEFAULT_COMMODITY}"]'
        
        try:
            await page.wait_for_selector(
                option_selector,
                state="attached",
                timeout=30_000,
            )
            print("[COT PDF] Commodity option found.")
        except Exception as e:
            print(f"[COT PDF] ERROR: Could not find commodity option - CFTC data may not be available yet")
            print(f"[COT PDF] Error details: {e}")
            await browser.close()
            sys.exit(1)  # Exit with error so retry logic triggers

        # ── Select commodity ──────────────────────────────────────────────
        try:
            await page.select_option("#commoditySelect", DEFAULT_COMMODITY)
            print(f"[COT PDF] Selected commodity: {DEFAULT_COMMODITY}")
        except Exception as e:
            print(f"[COT PDF] ERROR selecting commodity: {e}")
            await browser.close()
            sys.exit(1)

        await page.wait_for_timeout(500)

        # ── Click Generate Charts and wait for data ───────────────────────
        print(f"[COT PDF] Clicking Generate Charts...")
        await page.click("#fetchBtn")
        
        print(f"[COT PDF] Waiting up to {API_WAIT_MS/1000:.0f}s for CFTC data...")
        
        # Wait for the loading spinner to disappear
        try:
            await page.wait_for_function(
                "() => document.getElementById('loading').style.display === 'none' || document.getElementById('loading').style.display === ''",
                timeout=API_WAIT_MS,
            )
        except Exception as e:
            print(f"[COT PDF] ERROR: Loading timeout - CFTC data not available")
            print(f"[COT PDF] Error details: {e}")
            await browser.close()
            sys.exit(1)

        # ── Validate that data was actually loaded ─────────────────────────
        # Check if charts have data by looking for canvas elements with content
        try:
            chart_count = await page.evaluate("""() => {
                const canvases = document.querySelectorAll('canvas');
                let validCharts = 0;
                canvases.forEach(canvas => {
                    const chart = Chart.getChart(canvas);
                    if (chart && chart.data && chart.data.datasets && chart.data.datasets.length > 0) {
                        validCharts++;
                    }
                });
                return validCharts;
            }""")
            
            if chart_count == 0:
                print(f"[COT PDF] ERROR: No valid chart data found - CFTC report may not be published yet")
                await browser.close()
                sys.exit(1)
                
            print(f"[COT PDF] Found {chart_count} valid charts with data")
            
        except Exception as e:
            print(f"[COT PDF] Warning: Could not validate chart data: {e}")
            # Continue anyway - validation is best-effort

        # ── Wait for all sections to be visible ───────────────────────────
        print("[COT PDF] Waiting for all chart sections to render...")
        
        chart_sections = [
            "#chart1",  # Position Analysis
            "#chart2",  # All Trader Categories  
            "#chart3",  # Trader Count
            "#chart4",  # Position Size
            "#weeklyDetail",  # Weekly Detail
            "#execSec",  # Executive Summary
            "#sumSec",  # Market Summary
        ]
        
        for section in chart_sections:
            try:
                await page.wait_for_selector(
                    section,
                    state="visible",
                    timeout=15_000,
                )
                print(f"[COT PDF] Section {section} visible.")
            except Exception as e:
                print(f"[COT PDF] Warning: Section {section} not visible: {e}")

        # Extra safety wait for any final rendering
        await page.wait_for_timeout(3_000)

        # ── Emulate print media for proper chart sizing ─────────────────────
        print("[COT PDF] Emulating print media for proper chart sizing...")
        await page.emulate_media(media="print")
        
        # Wait for Chart.js to redraw after media change
        await page.wait_for_timeout(2_000)
        
        # Trigger window resize to force chart redraw
        await page.evaluate("() => { window.dispatchEvent(new Event('resize')); }")
        await page.wait_for_timeout(1_000)
        
        print("[COT PDF] All sections rendered. Generating PDF...")

        # Export PDF
        pdf_bytes = await page.pdf(**PDF_OPTIONS)
        OUTPUT_PDF.write_bytes(pdf_bytes)
        
        # Validate PDF was created with content
        if OUTPUT_PDF.stat().st_size < 1000:
            print(f"[COT PDF] ERROR: PDF file too small ({OUTPUT_PDF.stat().st_size} bytes) - may be empty")
            await browser.close()
            sys.exit(1)
        
        print(f"[COT PDF] PDF saved to: {OUTPUT_PDF} ({len(pdf_bytes)/1024:.1f} KB)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(generate())
