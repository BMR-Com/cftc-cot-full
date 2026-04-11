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

COTTON_DISPLAY_NAME = "Cotton"

ET = tz.gettz('US/Eastern')

API_WAIT_MS = 180_000
CHART_RENDER_MS = 120_000

# A4 Portrait: 210mm x 297mm (8.27 x 11.69 inches)
PDF_OPTIONS = {
    "format": "A4",
    "landscape": False,  # Portrait mode
    "print_background": True,
    "prefer_css_page_size": False,
    "margin": {
        "top": "0mm",
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
    generation_date = datetime.now(ET).strftime("%Y-%m-%d %H:%M %Z")
    
    print(f"[COT PDF] Report Date (Tuesday): {report_date}")
    print(f"[COT PDF] Generated: {generation_date}")

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
        
        # Portrait viewport
        page = await browser.new_page(viewport={"width": 1000, "height": 1400})
        
        # A4 Portrait: 210mm x 297mm
        combined_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>COT Report - {report_date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        @page {{
            size: 210mm 297mm;  /* A4 Portrait: width 210mm, height 297mm */
            margin: 10mm;
        }}
        
        @page :first {{
            margin: 0;
        }}
        
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        
        /* Cover Page - A4 Portrait: 210mm x 297mm */
        .cover-page {{
            width: 210mm;
            height: 297mm;
            position: relative;
            page-break-after: always;
            break-after: page;
            overflow: hidden;
            margin: 0;
            padding: 0;
        }}
        
        .cover-page img.cover-image {{
            position: absolute;
            top: 0;
            left: 0;
            width: 210mm;
            height: 297mm;
            object-fit: cover;
            object-position: center;
            display: block;
        }}
        
        .cover-footer {{
            position: absolute;
            bottom: 15mm;
            right: 15mm;
            font-family: Arial, sans-serif;
            font-size: 12px;
            color: #333;
            background: rgba(255,255,255,0.95);
            padding: 8px 15px;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            z-index: 10;
        }}
        
        #reportContainer {{
            width: 100%;
            min-height: 277mm;
        }}
        
        #loadingMsg {{
            text-align: center;
            padding: 50px;
            font-family: Arial;
        }}
    </style>
</head>
<body>
    <!-- Cover Page -->
    <div class="cover-page">
        <img class="cover-image" src="{cover_base64 or ''}" alt="Cover" />
        <div class="cover-footer">Report Date: {report_date}</div>
    </div>
    
    <!-- Report Content -->
    <div id="reportContainer">
        <div id="loadingMsg">Loading COT Report...</div>
    </div>
    
    <script>
        async function loadReport() {{
            try {{
                const response = await fetch('{HTML_FILE.resolve().as_uri()}');
                const html = await response.text();
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const bodyContent = doc.body.innerHTML;
                document.getElementById('reportContainer').innerHTML = bodyContent;
                
                const scripts = doc.querySelectorAll('script');
                scripts.forEach(oldScript => {{
                    const newScript = document.createElement('script');
                    if (oldScript.src) {{
                        newScript.src = oldScript.src;
                    }} else {{
                        newScript.textContent = oldScript.textContent;
                    }}
                    document.body.appendChild(newScript);
                }});
                
                const links = doc.querySelectorAll('link[rel="stylesheet"]');
                links.forEach(link => {{
                    if (!document.querySelector(`link[href="${{link.href}}"]`)) {{
                        const newLink = document.createElement('link');
                        newLink.rel = 'stylesheet';
                        newLink.href = link.href;
                        document.head.appendChild(newLink);
                    }}
                }});
            }} catch (err) {{
                document.getElementById('loadingMsg').innerHTML = 'Error loading report: ' + err.message;
            }}
        }}
        loadReport();
    </script>
</body>
</html>"""
        
        await page.set_content(combined_html)
        print("[COT PDF] Combined page loaded")
        
        print("[COT PDF] Waiting for report content to load...")
        await page.wait_for_timeout(3_000)
        
        try:
            await page.wait_for_selector('#commoditySelect option', state="attached", timeout=30_000)
            
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

        try:
            await page.select_option("#commoditySelect", selected_value)
            print(f"[COT PDF] Selected commodity: {selected_value}")
        except Exception as e:
            print(f"[COT PDF] ERROR selecting commodity: {e}")
            await browser.close()
            sys.exit(1)

        await page.wait_for_timeout(500)

        print("[COT PDF] Clicking Generate Charts...")
        try:
            await page.click("#fetchBtn")
        except Exception as e:
            print(f"[COT PDF] ERROR clicking Generate Charts button: {e}")
            await browser.close()
            sys.exit(1)
        
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

        try:
            await page.wait_for_selector('#weeklyDetail tbody tr, #weeklyDetail table tr', timeout=30_000)
            print("[COT PDF] Table content found")
        except Exception as e:
            print(f"[COT PDF] WARNING: Table content timeout: {e}")

        sections = ["#chart1", "#chart2", "#chart3", "#chart4", "#weeklyDetail", "#execSec", "#sumSec"]
        print("[COT PDF] Verifying all sections visible...")
        for section in sections:
            try:
                await page.wait_for_selector(section, state="visible", timeout=15_000)
                print(f"[COT PDF] ✓ {section}")
            except Exception as e:
                print(f"[COT PDF] ⚠ {section} not visible: {e}")

        print("[COT PDF] Final rendering wait (5 seconds)...")
        await page.wait_for_timeout(5_000)

        print("[COT PDF] Emulating print media...")
        await page.emulate_media(media="print")
        await page.wait_for_timeout(3_000)
        
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
