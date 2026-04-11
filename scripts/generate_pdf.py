"""
generate_pdf.py
Loads the BCOM COT Analyzer HTML page in a headless Chromium browser,
waits for all charts to render, then exports to PDF with cover page.
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
COVER_PAGE_PATH = Path(__file__).parent.parent / "assets" / "cover_page.png"
LOGO_PATH = Path(__file__).parent.parent / "assets" / "tullett_prebon_logo.png"

ET = tz.gettz('US/Eastern')

API_WAIT_MS = 180_000
CHART_RENDER_MS = 120_000

PDF_OPTIONS = {
    "format": "A4",
    "landscape": True,
    "print_background": True,
    "prefer_css_page_size": False,
    "margin": {
        "top": "0mm",      # No margin for cover page
        "bottom": "0mm",
        "left": "0mm",
        "right": "0mm",
    },
}


def encode_image_base64(image_path):
    """Encode image to base64 for embedding in HTML."""
    if not image_path.exists():
        print(f"[COT PDF] Warning: Image not found at {image_path}")
        return None
    
    try:
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode('utf-8')
            ext = image_path.suffix.lower().replace('.', '')
            if ext == 'jpg':
                ext = 'jpeg'
            return f"data:image/{ext};base64,{encoded}"
    except Exception as e:
        print(f"[COT PDF] Warning: Could not encode image: {e}")
        return None


def get_report_date():
    """Get the report date (Tuesday of current week)."""
    today = datetime.now(ET)
    days_since_tuesday = (today.weekday() - 1) % 7
    tuesday = today - __import__('datetime').timedelta(days=days_since_tuesday)
    return tuesday.strftime("%B %d, %Y")


async def generate():
    report_date = get_report_date()
    print(f"[COT PDF] Report Date: {report_date}")
    print(f"[COT PDF] Starting PDF generation...")

    if not HTML_FILE.exists():
        print(f"ERROR: HTML file not found at {HTML_FILE}")
        sys.exit(1)

    cover_base64 = encode_image_base64(COVER_PAGE_PATH)
    logo_base64 = encode_image_base64(LOGO_PATH)

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

        # ── Inject Cover Page (Full Page Image with Footer) ────────────────
        if cover_base64:
            print("[COT PDF] Injecting cover page...")
            
            cover_html = f"""
            <style>
                @media print {{
                    @page :first {{
                        margin: 0 !important;
                        padding: 0 !important;
                    }}
                    
                    #tp-cover-page {{
                        page-break-after: always !important;
                        break-after: page !important;
                        width: 297mm !important;
                        height: 210mm !important;
                        margin: 0 !important;
                        padding: 0 !important;
                        position: relative !important;
                        overflow: hidden !important;
                    }}
                    
                    #tp-cover-image {{
                        width: 100% !important;
                        height: 100% !important;
                        object-fit: cover !important;
                        object-position: center !important;
                    }}
                    
                    #tp-cover-footer {{
                        position: absolute !important;
                        bottom: 15mm !important;
                        right: 15mm !important;
                        font-family: Arial, sans-serif !important;
                        font-size: 12px !important;
                        color: #666 !important;
                        background: rgba(255,255,255,0.9) !important;
                        padding: 8px 15px !important;
                        border-radius: 4px !important;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }}
                    
                    #tp-watermark {{
                        position: fixed !important;
                        top: 50% !important;
                        left: 50% !important;
                        transform: translate(-50%, -50%) rotate(-30deg) !important;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }}
                }}
            </style>
            
            <!-- Cover Page - Full Page Image with Footer -->
            <div id="tp-cover-page">
                <img id="tp-cover-image" src="{cover_base64}" />
                <div id="tp-cover-footer">Report Date: {report_date}</div>
            </div>
            """
            
            # Add watermark if logo exists
            if logo_base64:
                cover_html += f"""
                <!-- Watermark - All Pages (except cover) -->
                <div id="tp-watermark" style="
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%) rotate(-30deg);
                    opacity: 0.06;
                    pointer-events: none;
                    z-index: -1;
                    width: 400px;
                    height: auto;
                ">
                    <img src="{logo_base64}" style="width: 100%; height: auto; filter: grayscale(100%);" />
                </div>
                """
            
            await page.evaluate(f"""() => {{
                const cover = document.createElement('div');
                cover.innerHTML = `{cover_html}`;
                document.body.insertBefore(cover, document.body.firstChild);
            }}""")
            
            await page.add_style_tag(content="""
                @media print {
                    @page :first {
                        margin: 0 !important;
                        padding: 0 !important;
                    }
                    
                    #tp-cover-page {
                        page-break-after: always !important;
                        break-after: page !important;
                        width: 297mm !important;
                        height: 210mm !important;
                        margin: 0 !important;
                        padding: 0 !important;
                        position: relative !important;
                        overflow: hidden !important;
                    }
                    
                    #tp-cover-image {
                        width: 100% !important;
                        height: 100% !important;
                        object-fit: cover !important;
                        object-position: center !important;
                    }
                    
                    #tp-cover-footer {
                        position: absolute !important;
                        bottom: 15mm !important;
                        right: 15mm !important;
                        font-family: Arial, sans-serif !important;
                        font-size: 12px !important;
                        color: #666 !important;
                        background: rgba(255,255,255,0.9) !important;
                        padding: 8px 15px !important;
                        border-radius: 4px !important;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }
                    
                    #tp-watermark {
                        position: fixed !important;
                        top: 50% !important;
                        left: 50% !important;
                        transform: translate(-50%, -50%) rotate(-30deg) !important;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }
                    
                    /* Reset margins for other pages */
                    @page {
                        margin: 10mm !important;
                    }
                }
            """)
        
        # ── Wait for commodity dropdown and generate charts ───────────────
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
            await browser.close()
            sys.exit(1)

        # ── Select commodity and generate charts ───────────────────────────
        try:
            await page.select_option("#commoditySelect", selected_value)
            print(f"[COT PDF] Selected commodity: {selected_value}")
        except Exception as e:
            print(f"[COT PDF] ERROR selecting commodity: {e}")
            await browser.close()
            sys.exit(1)

        await page.wait_for_timeout(500)

        print(f"[COT PDF] Clicking Generate Charts...")
        
        try:
            await page.click("#fetchBtn")
        except Exception as e:
            print(f"[COT PDF] ERROR clicking Generate Charts button: {e}")
            await browser.close()
            sys.exit(1)
        
        # ── Wait for data loading ──────────────────────────────────────────
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
                """() =>
