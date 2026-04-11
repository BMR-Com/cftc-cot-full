"""
generate_pdf.py
Loads the BCOM COT Analyzer HTML page in a headless Chromium browser,
waits for all charts to render, then exports to PDF with cover page.

Cover page approach (tested):
  - Rendered in a SEPARATE browser page with margin=0
  - Black background with cover image centered (object-fit:contain)
  - Report date shown in footer overlay
  - Merged with report pages using pypdf
  - Watermark logo injected on all report pages via position:fixed
"""

import asyncio
import base64
import io
import sys
from pathlib import Path
from datetime import datetime
from dateutil import tz
from playwright.async_api import async_playwright
from pypdf import PdfWriter, PdfReader

# ── Config ─────────────────────────────────────────────────────────────────
HTML_FILE       = Path(__file__).parent.parent / "index.html"
OUTPUT_PDF      = Path(__file__).parent.parent / "cot_report.pdf"
COVER_PAGE_PATH = Path(__file__).parent.parent / "assets" / "cover_page.png"
LOGO_PATH       = Path(__file__).parent.parent / "assets" / "tullett_prebon_logo.png"

COTTON_DISPLAY_NAME = "Cotton"

ET = tz.gettz('US/Eastern')

API_WAIT_MS     = 180_000
CHART_RENDER_MS = 120_000

# Same custom page size as your original
REPORT_PDF_OPTIONS = {
    "width": "11.71in",
    "height": "8.28in",
    "print_background": True,
    "prefer_css_page_size": False,
    "margin": {
        "top":    "0mm",
        "bottom": "0mm",
        "left":   "0mm",
        "right":  "0mm",
    },
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def encode_image_base64(image_path: Path):
    """Encode image to base64 data-URI for embedding in HTML."""
    if not image_path.exists():
        print(f"[COT PDF] Warning: Image not found at {image_path}")
        return None
    try:
        ext = image_path.suffix.lower().lstrip(".")
        if ext == "jpg":
            ext = "jpeg"
        data = base64.b64encode(image_path.read_bytes()).decode()
        return f"data:image/{ext};base64,{data}"
    except Exception as e:
        print(f"[COT PDF] Warning: Could not encode image: {e}")
        return None


def get_report_date() -> str:
    """Return the Tuesday of the current week (formatted)."""
    import datetime as dt
    today = datetime.now(ET)
    days_since_tuesday = (today.weekday() - 1) % 7
    tuesday = today - dt.timedelta(days=days_since_tuesday)
    return tuesday.strftime("%B %d, %Y")


def build_cover_html(cover_b64: str, logo_b64: str, report_date: str) -> str:
    """
    Cover page HTML:
      - Black background fills the full page
      - Cover image is centered with object-fit:contain (no cropping)
      - Report date shown in a semi-transparent footer in the bottom-right
      - Watermark logo shown faintly behind the cover image
    Uses string concat to avoid CSS-brace conflicts with Python f-strings.
    """
    watermark = ""
    if logo_b64:
        watermark = (
            '<div style="position:fixed;top:50%;left:50%;'
            'transform:translate(-50%,-50%) rotate(-30deg);'
            'opacity:0.06;width:400px;pointer-events:none;z-index:0;'
            '-webkit-print-color-adjust:exact;print-color-adjust:exact;">'
            '<img src="' + logo_b64 + '" style="width:100%;height:auto;filter:grayscale(100%);" />'
            '</div>'
        )

    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<style>'
        '* { margin:0; padding:0; box-sizing:border-box; }'
        'html, body {'
        '  width:11.71in; height:8.28in; overflow:hidden;'
        '  background:#000000;'                   # black background
        '  display:flex; align-items:center; justify-content:center;'
        '  -webkit-print-color-adjust:exact; print-color-adjust:exact;'
        '}'
        'img#cover {'
        '  max-width:100%; max-height:100%;'
        '  object-fit:contain;'                   # centered, no cropping
        '  display:block;'
        '}'
        'div#footer {'
        '  position:fixed; bottom:10mm; right:12mm;'
        '  font-family:Arial,sans-serif; font-size:11px; color:#ffffff;'
        '  background:rgba(0,0,0,0.55); padding:5px 11px;'
        '  border-radius:3px; z-index:10;'
        '  -webkit-print-color-adjust:exact; print-color-adjust:exact;'
        '}'
        '</style></head><body>'
        + watermark
        + '<img id="cover" src="' + cover_b64 + '" />'
        + '<div id="footer">Report Date: ' + report_date + '</div>'
        + '</body></html>'
    )


def build_watermark_snippet(logo_b64: str) -> str:
    """
    HTML snippet injected into the main report page.
    position:fixed means the watermark appears on every printed page.
    Uses string concat to avoid CSS-brace conflicts with page.evaluate().
    """
    return (
        '<style>'
        '#tp-watermark {'
        '  position:fixed; top:50%; left:50%;'
        '  transform:translate(-50%,-50%) rotate(-30deg);'
        '  opacity:0.06; width:400px; pointer-events:none; z-index:0;'
        '  -webkit-print-color-adjust:exact; print-color-adjust:exact;'
        '}'
        '#tp-watermark img { width:100%; height:auto; filter:grayscale(100%); }'
        '</style>'
        '<div id="tp-watermark"><img src="' + logo_b64 + '" /></div>'
    )


# ── Main ────────────────────────────────────────────────────────────────────

async def generate():
    report_date     = get_report_date()
    generation_date = datetime.now(ET).strftime("%Y-%m-%d %H:%M %Z")

    print(f"[COT PDF] Report Date (Tuesday): {report_date}")
    print(f"[COT PDF] Generated:             {generation_date}")

    if not HTML_FILE.exists():
        print(f"ERROR: HTML file not found at {HTML_FILE}")
        sys.exit(1)

    cover_base64 = encode_image_base64(COVER_PAGE_PATH)
    logo_base64  = encode_image_base64(LOGO_PATH)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        # ── STEP 1: Cover page — own browser page, zero margins ────────────
        cover_pdf_bytes = None
        if cover_base64:
            print("[COT PDF] Generating cover page...")
            cp = await browser.new_page(viewport={"width": 1587, "height": 1123})
            await cp.set_content(
                build_cover_html(cover_base64, logo_base64, report_date),
                wait_until="load",
            )
            await cp.wait_for_timeout(400)
            cover_pdf_bytes = await cp.pdf(
                width="11.71in",
                height="8.28in",
                print_background=True,
                prefer_css_page_size=False,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            await cp.close()
            print("[COT PDF] ✓ Cover page generated")
        else:
            print("[COT PDF] Skipping cover page (image not found)")

        # ── STEP 2: Main report page ───────────────────────────────────────
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        file_url = HTML_FILE.resolve().as_uri()
        print(f"[COT PDF] Loading report: {file_url}")

        try:
            await page.goto(file_url, wait_until="networkidle", timeout=60_000)
        except Exception as e:
            print(f"[COT PDF] ERROR: Page load failed: {e}")
            await browser.close()
            sys.exit(1)

        # Inject watermark on every report page
        if logo_base64:
            print("[COT PDF] Injecting watermark on report pages...")
            await page.evaluate(
                """(html) => {
                    const div = document.createElement('div');
                    div.innerHTML = html;
                    document.body.insertBefore(div, document.body.firstChild);
                }""",
                build_watermark_snippet(logo_base64),
            )

        # ── Wait for commodity dropdown ────────────────────────────────────
        print("[COT PDF] Waiting for commodity list...")
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
                let opt = options.find(o =>
                    o.getAttribute('data-cn') &&
                    o.getAttribute('data-cn').toLowerCase().includes('cotton')
                );
                if (!opt) opt = options.find(o => o.textContent.toLowerCase().includes('cotton'));
                if (!opt) opt = options.find(o => o.value.toUpperCase().includes('COTTON'));
                return opt ? opt.value : null;
            }""")

            if cotton_value:
                selected_value = cotton_value
                print(f"[COT PDF] Found Cotton: {selected_value}")
            else:
                first_value = await page.evaluate("""() => {
                    const select = document.getElementById('commoditySelect');
                    if (!select) return null;
                    const options = Array.from(select.options);
                    const first = options.find(o => o.value && o.value.trim() !== '');
                    return first ? first.value : null;
                }""")
                if not first_value:
                    raise Exception("No valid commodity options found")
                selected_value = first_value
                print(f"[COT PDF] Cotton not found, using: {selected_value}")

        except Exception as e:
            print(f"[COT PDF] ERROR: Commodity list issue — {e}")
            try:
                opts = await page.evaluate("""() => {
                    const s = document.getElementById('commoditySelect');
                    if (!s) return [];
                    return Array.from(s.options).map(o => ({
                        value: o.value, text: o.textContent.trim(),
                        dataCn: o.getAttribute('data-cn')
                    }));
                }""")
                print(f"[COT PDF] First 5 options: {opts[:5]}")
            except Exception:
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

        # ── Click Generate Charts ──────────────────────────────────────────
        print("[COT PDF] Clicking Generate Charts...")
        try:
            await page.click("#fetchBtn")
        except Exception as e:
            print(f"[COT PDF] ERROR clicking Generate Charts: {e}")
            await browser.close()
            sys.exit(1)

        # ── Wait for loading spinner ───────────────────────────────────────
        print(f"[COT PDF] Waiting up to {API_WAIT_MS/1000:.0f}s for CFTC API data...")
        try:
            await page.wait_for_function(
                """() => {
                    const el = document.getElementById('loading');
                    return !el || el.style.display === 'none' ||
                           el.style.display === '' || el.classList.contains('hidden');
                }""",
                timeout=API_WAIT_MS,
            )
            print("[COT PDF] Data loading complete")
        except Exception as e:
            print(f"[COT PDF] ERROR: Loading timeout — {e}")
            await browser.close()
            sys.exit(1)

        # ── Get report date from page if available ─────────────────────────
        try:
            page_report_date = await page.evaluate("""() => {
                const dateElement = document.querySelector('.report-date, #reportDate, [data-report-date]');
                if (dateElement) return dateElement.textContent.trim();
                const canvas = document.querySelector('canvas');
                if (canvas) {
                    const chart = Chart.getChart(canvas);
                    if (chart && chart.data && chart.data.labels && chart.data.labels.length > 0) {
                        const lastLabel = chart.data.labels[chart.data.labels.length - 1];
                        if (lastLabel) return lastLabel;
                    }
                }
                return null;
            }""")
            if page_report_date:
                report_date = page_report_date
                print(f"[COT PDF] Report date from page: {report_date}")
            else:
                print(f"[COT PDF] Using calculated report date: {report_date}")
        except Exception:
            print(f"[COT PDF] Using calculated report date: {report_date}")

        # ── Wait for charts ────────────────────────────────────────────────
        print(f"[COT PDF] Waiting up to {CHART_RENDER_MS/1000:.0f}s for charts...")
        try:
            await page.wait_for_function(
                """() => {
                    const canvases = document.querySelectorAll('canvas');
                    if (canvases.length === 0) return false;
                    let chartsWithData = 0;
                    canvases.forEach(canvas => {
                        const chart = Chart.getChart(canvas);
                        if (chart && chart.data && chart.data.datasets &&
                                chart.data.datasets.length > 0) {
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

        # ── Wait for table ─────────────────────────────────────────────────
        print("[COT PDF] Waiting for table content...")
        try:
            await page.wait_for_selector(
                '#weeklyDetail tbody tr, #weeklyDetail table tr',
                timeout=30_000,
            )
            print("[COT PDF] Table content found")
        except Exception as e:
            print(f"[COT PDF] WARNING: Table content timeout: {e}")

        # ── Verify sections ────────────────────────────────────────────────
        sections = ["#chart1", "#chart2", "#chart3", "#chart4",
                    "#weeklyDetail", "#execSec", "#sumSec"]
        print("[COT PDF] Verifying all sections visible...")
        for section in sections:
            try:
                await page.wait_for_selector(section, state="visible", timeout=15_000)
                print(f"[COT PDF] ✓ {section}")
            except Exception as e:
                print(f"[COT PDF] ⚠ {section} not visible: {e}")

        print("[COT PDF] Final rendering wait (5 seconds)...")
        await page.wait_for_timeout(5_000)

        # ── Generate report PDF ────────────────────────────────────────────
        print("[COT PDF] Emulating print media...")
        await page.emulate_media(media="print")
        await page.wait_for_timeout(3_000)

        await page.evaluate("() => { window.dispatchEvent(new Event('resize')); }")
        await page.wait_for_timeout(2_000)

        print("[COT PDF] Generating report PDF...")
        report_pdf_bytes = await page.pdf(**REPORT_PDF_OPTIONS)

        await browser.close()

        # ── STEP 3: Merge cover (page 1) + report pages ────────────────────
        if cover_pdf_bytes:
            print("[COT PDF] Merging cover + report pages...")
            writer = PdfWriter()
            for pg in PdfReader(io.BytesIO(cover_pdf_bytes)).pages:
                writer.add_page(pg)
            for pg in PdfReader(io.BytesIO(report_pdf_bytes)).pages:
                writer.add_page(pg)
            with open(OUTPUT_PDF, "wb") as f:
                writer.write(f)
            print("[COT PDF] ✓ PDFs merged")
        else:
            OUTPUT_PDF.write_bytes(report_pdf_bytes)

        pdf_size = OUTPUT_PDF.stat().st_size
        if pdf_size < 10_000:
            print(f"[COT PDF] ERROR: PDF too small ({pdf_size} bytes)")
            sys.exit(1)

        print(f"[COT PDF] ✓ PDF saved: {OUTPUT_PDF} ({pdf_size / 1024:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(generate())
