"""
generate_pdf.py
Loads the BCOM COT Analyzer HTML page in a headless Chromium browser,
waits for all charts to render, then exports to PDF with Tullett Prebon Agriculture branding.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from dateutil import tz
from playwright.async_api import async_playwright
import base64

# ── Config ─────────────────────────────────────────────────────────────────
HTML_FILE = Path(__file__).parent.parent / "index.html"
OUTPUT_PDF = Path(__file__).parent.parent / "cot_report.pdf"
LOGO_PATH = Path(__file__).parent.parent / "assets" / "tullett_prebon_logo.png"

ET = tz.gettz('US/Eastern')

# INCREASED TIMEOUTS for chart rendering (you mentioned 60+ seconds)
API_WAIT_MS = 180_000      # 3 minutes for CFTC API data loading
CHART_RENDER_MS = 120_000  # 2 minutes for chart rendering after data loaded
TOTAL_TIMEOUT_MS = 300_000 # 5 minutes total page timeout

PDF_OPTIONS = {
    "format": "A4",
    "landscape": True,
    "print_background": True,
    "prefer_css_page_size": True,
    "margin": {
        "top": "15mm",
        "bottom": "8mm",
        "left": "10mm",
        "right": "10mm",
    },
}


def get_expected_report_date():
    """Calculate the expected Tuesday report date for current week."""
    today = datetime.now(ET)
    days_since_tuesday = (today.weekday() - 1) % 7
    tuesday = today - __import__('datetime').timedelta(days=days_since_tuesday)
    return tuesday.strftime("%Y-%m-%d")


def encode_logo_base64():
    """Encode logo image to base64 for embedding in HTML."""
    if not LOGO_PATH.exists():
        print(f"[COT PDF] Warning: Logo not found at {LOGO_PATH}")
        return None
    
    try:
        with open(LOGO_PATH, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
    except Exception as e:
        print(f"[COT PDF] Warning: Could not encode logo: {e}")
        return None


async def generate():
    now_et = datetime.now(ET)
    date_str = now_et.strftime("%Y-%m-%d")
    expected_report = get_expected_report_date()
    
    print(f"[COT PDF] Starting generation for report week: {date_str}")
    print(f"[COT PDF] Expected CFTC report date (Tuesday): {expected_report}")

    if not HTML_FILE.exists():
        print(f"ERROR: HTML file not found at {HTML_FILE}")
        sys.exit(1)

    logo_base64 = encode_logo_base64()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        file_url = HTML_FILE.resolve().as_uri()
        print(f"[COT PDF] Loading: {file_url}")

        try:
            await page.goto(file_url, wait_until="networkidle", timeout=60_000)
        except Exception as e:
            print(f"[COT PDF] ERROR: Page load failed: {e}")
            await browser.close()
            sys.exit(1)

        # ── Inject Logo Header ─────────────────────────────────────────────
        if logo_base64:
            print("[COT PDF] Injecting Tullett Prebon Agriculture branding...")
            
            header_html = f"""
            <div id="tp-header" style="
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 50px;
                background: white;
                border-bottom: 2px solid #0072C6;
                display: flex;
                align-items: center;
                padding: 0 20px;
                z-index: 1000;
                box-sizing: border-box;
            ">
                <img src="{logo_base64}" style="height: 35px; width: auto;" />
                <div style="
                    margin-left: auto;
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                    color: #666;
                ">
                    COT Report: {expected_report} | Generated: {date_str}
                </div>
            </div>
            <div style="height: 60px;"></div>
            """
            
            await page.evaluate(f"""() => {{
                const header = document.createElement('div');
                header.innerHTML = `{header_html}`;
                document.body.insertBefore(header.firstElementChild, document.body.firstChild);
                const spacer = document.createElement('div');
                spacer.style.height = '60px';
                document.body.insertBefore(spacer, document.body.children[1]);
            }}""")
            
            await page.add_style_tag(content="""
                @media print {
                    #tp-header { position: fixed; top: 0; }
                    body { padding-top: 60px !important; }
                }
            """)
        
        # ── Wait for commodity dropdown ───────────────────────────────────
        print("[COT PDF] Waiting for commodity list to populate...")
        
        try:
            await page.wait_for_selector(
                '#commoditySelect option[value]',
                state="attached",
                timeout=30_000,
            )
            
            first_option = await page.eval_on_selector(
                '#commoditySelect option[value]', 
                'el => el.value'
            )
            
            if not first_option:
                raise Exception("No commodities found in dropdown")
                
            print(f"[COT PDF] Found commodity: {first_option}")
            
        except Exception as e:
            print(f"[COT PDF] ERROR: Commodity list not populated - CFTC data may not be available yet")
            await browser.close()
            sys.exit(1)

        # ── Select commodity and generate charts ───────────────────────────
        try:
            await page.select_option("#commoditySelect", first_option)
            print(f"[COT PDF] Selected commodity: {first_option}")
        except Exception as e:
            print(f"[COT PDF] ERROR selecting commodity: {e}")
            await browser.close()
            sys.exit(1)

        await page.wait_for_timeout(500)

        print(f"[COT PDF] Clicking Generate Charts...")
        await page.click("#fetchBtn")
        
        # ── Wait for loading spinner to disappear (data loaded) ─────────────
        print(f"[COT PDF] Waiting up to {API_WAIT_MS/1000:.0f}s for CFTC API data...")
        
        try:
            await page.wait_for_function(
                """() => {
                    const el = document.getElementById('loading');
                    return !el || el.style.display === 'none' || el.style.display === '' || el.classList.contains('hidden');
                }""",
                timeout=API_WAIT_MS,
            )
            print("[COT PDF] Data loading complete")
        except Exception as e:
            print(f"[COT PDF] ERROR: Loading timeout - CFTC data not available")
            await browser.close()
            sys.exit(1)

        # ── ADDITIONAL WAIT: Ensure charts are fully rendered ───────────────
        print(f"[COT PDF] Waiting up to {CHART_RENDER_MS/1000:.0f}s for charts to render...")
        
        try:
            # Wait for Chart.js instances to be ready with data
            await page.wait_for_function(
                """() => {
                    const canvases = document.querySelectorAll('canvas');
                    if (canvases.length === 0) return false;
                    
                    let chartsWithData = 0;
                    canvases.forEach(canvas => {
                        const chart = Chart.getChart(canvas);
                        if (chart && chart.data && chart.data.datasets && chart.data.datasets.length > 0) {
                            const hasData = chart.data.datasets.some(ds => 
                                ds.data && ds.data.length > 0 && 
                                ds.data.some(v => v !== null && v !== undefined)
                            );
                            if (hasData) chartsWithData++;
                        }
                    });
                    
                    // Expect at least 4 charts (chart1, chart2, chart3, chart4)
                    return chartsWithData >= 4;
                }""",
                timeout=CHART_RENDER_MS,
            )
            print("[COT PDF] Charts rendered successfully")
            
        except Exception as e:
            print(f"[COT PDF] WARNING: Chart rendering timeout: {e}")
            # Continue anyway - partial data is better than no email

        # ── Wait for table content ─────────────────────────────────────────
        print("[COT PDF] Waiting for table content...")
        
        try:
            # Wait for weekly detail table to have rows
            await page.wait_for_selector(
                '#weeklyDetail tbody tr, #weeklyDetail table tr',
                timeout=30_000,
            )
            print("[COT PDF] Table content found")
        except Exception as e:
            print(f"[COT PDF] WARNING: Table content timeout: {e}")

        # ── Wait for summary sections ───────────────────────────────────────
        chart_sections = [
            "#chart1", "#chart2", "#chart3", "#chart4",
            "#weeklyDetail", "#execSec", "#sumSec",
        ]
        
        print("[COT PDF] Verifying all sections visible...")
        for section in chart_sections:
            try:
                await page.wait_for_selector(section, state="visible", timeout=15_000)
                print(f"[COT PDF] ✓ {section}")
            except Exception as e:
                print(f"[COT PDF] ⚠ {section} not visible: {e}")

        # Extra wait for any final rendering
        print("[COT PDF] Final rendering wait (5 seconds)...")
        await page.wait_for_timeout(5_000)

        # ── Generate PDF ────────────────────────────────────────────────────
        print("[COT PDF] Emulating print media...")
        await page.emulate_media(media="print")
        await page.wait_for_timeout(3_000)
        
        # Force chart redraw
        await page.evaluate("() => { window.dispatchEvent(new Event('resize')); }")
        await page.wait_for_timeout(2_000)
        
        print("[COT PDF] Generating PDF...")
        
        pdf_bytes = await page.pdf(**PDF_OPTIONS)
        OUTPUT_PDF.write_bytes(pdf_bytes)
        
        pdf_size = OUTPUT_PDF.stat().st_size
        if pdf_size < 10_000:  # Less than 10KB is likely empty
            print(f"[COT PDF] ERROR: PDF file too small ({pdf_size} bytes)")
            await browser.close()
            sys.exit(1)
        
        print(f"[COT PDF] ✓ PDF saved: {OUTPUT_PDF} ({pdf_size/1024:.1f} KB)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(generate())
