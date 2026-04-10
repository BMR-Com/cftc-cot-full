"""
generate_pdf.py
Loads the BCOM COT Analyzer HTML page in a headless Chromium browser,
waits for all charts to render, then exports to PDF with Tullett Prebon Agriculture watermark.
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

# Cotton display name
COTTON_DISPLAY_NAME = "Cotton"

ET = tz.gettz('US/Eastern')

# INCREASED TIMEOUTS for chart rendering
API_WAIT_MS = 180_000
CHART_RENDER_MS = 120_000

PDF_OPTIONS = {
    "format": "A4",
    "landscape": True,
    "print_background": True,
    "prefer_css_page_size": False,  # Changed to use our margins
    "margin": {
        "top": "10mm",      # Reduced top margin
        "bottom": "10mm",
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

        # ── Inject Watermark Logo ──────────────────────────────────────────
        if logo_base64:
            print("[COT PDF] Injecting Tullett Prebon Agriculture watermark...")
            
            watermark_html = f"""
            <div id="tp-watermark" style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) rotate(-30deg);
                opacity: 0.08;
                pointer-events: none;
                z-index: 1000;
                width: 500px;
                height: auto;
            ">
                <img src="{logo_base64}" style="width: 100%; height: auto; filter: grayscale(100%);" />
            </div>
            <div id="tp-header" style="
                position: fixed;
                top: 5mm;
                right: 10mm;
                opacity: 0.9;
                z-index: 1001;
                display: flex;
                align-items: center;
                gap: 10px;
            ">
                <img src="{logo_base64}" style="height: 25px; width: auto;" />
                <span style="font-family: Arial, sans-serif; font-size: 10px; color: #666;">
                    {expected_report}
                </span>
            </div>
            """
            
            await page.evaluate(f"""() => {{
                const watermark = document.createElement('div');
                watermark.innerHTML = `{watermark_html}`;
                document.body.appendChild(watermark);
            }}""")
            
            # Add print styles to ensure watermark appears on all pages
            await page.add_style_tag(content="""
                @media print {
                    #tp-watermark {
                        position: fixed !important;
                        top: 50% !important;
                        left: 50% !important;
                        transform: translate(-50%, -50%) rotate(-30deg) !important;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }
                    #tp-header {
                        position: fixed !important;
                        top: 5mm !important;
                        right: 10mm !important;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }
                }
            """)
        
        # ── Wait for commodity dropdown ───────────────────────────────────
        print("[COT PDF] Waiting for commodity list to populate...")
        
        try:
            await page.wait_for_selector(
                '#commoditySelect option',
                state="attached",
                timeout=30_000,
            )
            
            cotton_value = await page.evaluate("""() => {
                const select = document.getElementById('commoditySelect');
                if (!select) return null;
                
                const options = Array.from(select.options);
                
                let cottonOpt = options.find(o => 
                    o.getAttribute('data-cn') && 
                    o.getAttribute('data-cn').toLowerCase().includes('cotton')
                );
                
                if (!cottonOpt) {
                    cottonOpt = options.find(o => 
                        o.textContent.toLowerCase().includes('cotton')
                    );
                }
                
                if (!cottonOpt) {
                    cottonOpt = options.find(o => 
                        o.value.toUpperCase().includes('COTTON')
                    );
                }
                
                return cottonOpt ? cottonOpt.value : null;
            }""")
            
            if cotton_value:
                selected_value = cotton_value
                print(f"[COT PDF] Found Cotton: {selected_value}")
            else:
                first_value = await page.evaluate("""() => {
                    const select = document.getElementById('commoditySelect');
                    if (!select) return null;
                    const options = Array.from(select.options);
                    const firstReal = options.find(o => o.value && o.value.trim() !== '');
                    return firstReal ? firstReal.value : null;
                }""")
                
                if not first_value:
                    raise Exception("No valid commodity options found")
                    
                selected_value = first_value
                print(f"[COT PDF] Cotton not found, using: {selected_value}")
            
        except Exception as e:
            print(f"[COT PDF] ERROR: Commodity list issue - {e}")
            try:
                all_options = await page.evaluate("""() => {
                    const select = document.getElementById('commoditySelect');
                    if (!select) return [];
                    return Array.from(select.options).map(o => ({
                        value: o.value,
                        text: o.textContent.trim(),
                        dataCn: o.getAttribute('data-cn')
                    }));
                }""")
                print(f"[COT PDF] All options: {all_options}")
            except:
                pass
            await browser.close()
            sys.exit(1)

        # ── Select commodity ───────────────────────────────────────────────
        try:
            await page.select_option("#commoditySelect", selected_value)
            print(f"[COT PDF] Selected commodity: {selected_value}")
        except Exception as e:
            print(f"[COT PDF] ERROR selecting commodity: {e}")
            await browser.close()
            sys.exit(1)

        await page.wait_for_timeout(500)

        # ── Click Generate Charts ─────────────────────────────────────────
        print(f"[COT PDF] Clicking Generate Charts...")
        
        try:
            await page.click("#fetchBtn")
        except Exception as e:
            print(f"[COT PDF] ERROR clicking Generate Charts button: {e}")
            await browser.close()
            sys.exit(1)
        
        # ── Wait for loading spinner to disappear ─────────────────────────
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
            print(f"[COT PDF] ERROR: Loading timeout - {e}")
            await browser.close()
            sys.exit(1)

        # ── Wait for charts to be fully rendered ───────────────────────────
        print(f"[COT PDF] Waiting up to {CHART_RENDER_MS/1000:.0f}s for charts to render...")
        
        try:
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
                    
                    return chartsWithData >= 4;
                }""",
                timeout=CHART_RENDER_MS,
            )
            print("[COT PDF] Charts rendered successfully")
            
        except Exception as e:
            print(f"[COT PDF] WARNING: Chart rendering timeout: {e}")

        # ── Wait for table content ─────────────────────────────────────────
        print("[COT PDF] Waiting for table content...")
        
        try:
            await page.wait_for_selector(
                '#weeklyDetail tbody tr, #weeklyDetail table tr',
                timeout=30_000,
            )
            print("[COT PDF] Table content found")
        except Exception as e:
            print(f"[COT PDF] WARNING: Table content timeout: {e}")

        # ── Wait for summary sections ───────────────────────────────────────
        sections = [
            "#chart1", "#chart2", "#chart3", "#chart4",
            "#weeklyDetail", "#execSec", "#sumSec",
        ]
        
        print("[COT PDF] Verifying all sections visible...")
        for section in sections:
            try:
                await page.wait_for_selector(section, state="visible", timeout=15_000)
                print(f"[COT PDF] ✓ {section}")
            except Exception as e:
                print(f"[COT PDF] ⚠ {section} not visible: {e}")

        # Extra wait for final rendering
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
        if pdf_size < 10_000:
            print(f"[COT PDF] ERROR: PDF file too small ({pdf_size} bytes)")
            await browser.close()
            sys.exit(1)
        
        print(f"[COT PDF] ✓ PDF saved: {OUTPUT_PDF} ({pdf_size/1024:.1f} KB)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(generate())
