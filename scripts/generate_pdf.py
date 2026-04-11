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

PDF_OPTIONS = {
    "format": "A4",
    "landscape": True,
    "print_background": True,
    "prefer_css_page_size": False,
    "margin": {
        "top": "10mm",
        "bottom": "10mm",
        "left": "10mm",
        "right": "10mm",
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

        # ── Generate Cover Page as a Separate PDF ──────────────────────────
        # This avoids the @page :first margin conflict with the main document.
        # The cover is rendered in its own page with zero margins so the image
        # bleeds edge-to-edge, then merged with pypdf at the end.
        cover_pdf_bytes = None
        if cover_base64:
            print("[COT PDF] Generating cover page as separate PDF...")

            cover_page = await browser.new_page(viewport={"width": 1587, "height": 1123})

            watermark_html = ""
            if logo_base64:
                watermark_html = f"""
                <img src="{logo_base64}"
                     style="position:fixed;top:50%;left:50%;
                            transform:translate(-50%,-50%) rotate(-30deg);
                            width:400px;opacity:0.06;filter:grayscale(100%);
                            pointer-events:none;z-index:0;" />
                """

            cover_full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{
    width: 297mm;
    height: 210mm;
    overflow: hidden;
    background: #fff;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  #cover-img {{
    display: block;
    position: fixed;
    top: 0; left: 0;
    width: 100%;
    height: 100%;
    object-fit: fill;
    z-index: 1;
  }}
  #cover-footer {{
    position: fixed;
    bottom: 12mm;
    right: 14mm;
    font-family: Arial, sans-serif;
    font-size: 11px;
    color: #333;
    background: rgba(255,255,255,0.92);
    padding: 6px 12px;
    border-radius: 3px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    z-index: 10;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
</style>
</head>
<body>
  <img id="cover-img" src="{cover_base64}" alt="Cover" />
  {watermark_html}
  <div id="cover-footer">Report Date: {report_date}</div>
</body>
</html>"""

            await cover_page.set_content(cover_full_html, wait_until="load")
            await cover_page.wait_for_timeout(500)

            cover_pdf_bytes = await cover_page.pdf(
                format="A4",
                landscape=True,
                print_background=True,
                prefer_css_page_size=False,
                # Zero margins so image bleeds fully to all edges
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            await cover_page.close()
            print("[COT PDF] Cover page PDF generated")

        # ── Main report page ───────────────────────────────────────────────
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        file_url = HTML_FILE.resolve().as_uri()
        print(f"[COT PDF] Loading: {file_url}")

        try:
            await page.goto(file_url, wait_until="networkidle", timeout=60_000)
        except Exception as e:
            print(f"[COT PDF] ERROR: Page load failed: {e}")
            await browser.close()
            sys.exit(1)

        # ── Wait for commodity dropdown to be populated ───────────────────
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
                print(f"[COT PDF] First 5 options: {all_options[:5]}")
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

        # ── Generate main report PDF ────────────────────────────────────────
        print("[COT PDF] Emulating print media...")
        await page.emulate_media(media="print")
        await page.wait_for_timeout(3_000)
        
        # Force chart redraw
        await page.evaluate("() => { window.dispatchEvent(new Event('resize')); }")
        await page.wait_for_timeout(2_000)
        
        print("[COT PDF] Generating main report PDF...")
        report_pdf_bytes = await page.pdf(**PDF_OPTIONS)

        await browser.close()

        # ── Merge cover + report PDFs ──────────────────────────────────────
        if cover_pdf_bytes:
            print("[COT PDF] Merging cover page with report...")
            try:
                from pypdf import PdfWriter, PdfReader
                import io

                writer = PdfWriter()

                # Page 1: cover (full-bleed, no margins)
                cover_reader = PdfReader(io.BytesIO(cover_pdf_bytes))
                for cp in cover_reader.pages:
                    writer.add_page(cp)

                # Remaining pages: main report
                report_reader = PdfReader(io.BytesIO(report_pdf_bytes))
                for rp in report_reader.pages:
                    writer.add_page(rp)

                with open(OUTPUT_PDF, "wb") as f:
                    writer.write(f)

                print("[COT PDF] PDFs merged successfully")

            except ImportError:
                print("[COT PDF] WARNING: pypdf not installed — saving report without cover page.")
                print("[COT PDF]          Install with: pip install pypdf")
                OUTPUT_PDF.write_bytes(report_pdf_bytes)
        else:
            OUTPUT_PDF.write_bytes(report_pdf_bytes)

        pdf_size = OUTPUT_PDF.stat().st_size
        if pdf_size < 10_000:
            print(f"[COT PDF] ERROR: PDF file too small ({pdf_size} bytes)")
            sys.exit(1)
        
        print(f"[COT PDF] ✓ PDF saved: {OUTPUT_PDF} ({pdf_size/1024:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(generate())
