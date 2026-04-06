"""
send_email.py
Sends the generated COT PDF report via SMTP email.

Reads credentials from environment variables (set as GitHub Secrets):
  SMTP_HOST  — e.g. smtp.gmail.com
  SMTP_PORT  — e.g. 587
  SMTP_USER  — your email address
  SMTP_PASS  — your app password (NOT your login password)
  EMAIL_FROM — sender address (usually same as SMTP_USER)
  EMAIL_TO   — comma-separated list of recipients

Gmail setup:
  1. Enable 2FA on your Google account
  2. Create an App Password at myaccount.google.com/apppasswords
  3. Use that 16-char password as SMTP_PASS

Outlook/Office365:
  SMTP_HOST=smtp.office365.com  SMTP_PORT=587
"""

import os
import smtplib
import sys
from datetime import datetime, timezone, timedelta
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────
PDF_PATH = Path(__file__).parent.parent / "cot_report.pdf"

def get_env(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        print(f"ERROR: Environment variable '{key}' is not set.")
        sys.exit(1)
    return val


def send():
    smtp_host = get_env("SMTP_HOST")
    smtp_port = int(get_env("SMTP_PORT"))
    smtp_user = get_env("SMTP_USER")
    smtp_pass = get_env("SMTP_PASS")
    email_from = get_env("EMAIL_FROM")
    email_to_raw = get_env("EMAIL_TO")
    recipients = [r.strip() for r in email_to_raw.split(",") if r.strip()]

    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}. Run generate_pdf.py first.")
        sys.exit(1)

    et = timezone(timedelta(hours=-5))  # EST
    now_et = datetime.now(et)
    date_str = now_et.strftime("%B %d, %Y")
    week_str = now_et.strftime("Week of %Y-%m-%d")

    # Build email
    msg = MIMEMultipart()
    msg["From"] = email_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"BCOM COT Weekly Report — {date_str}"

    body = f"""
<html><body>
<p>Please find attached the <strong>Bloomberg Commodity Index (BCOM) COT Weekly Report</strong>
for <strong>{date_str}</strong>.</p>

<p><strong>Report contents (A4 Landscape PDF):</strong></p>
<ul>
  <li>BCOM COT Executive Summary — Managed Money Positioning Extremes</li>
  <li>BCOM Market Summary — All Trader Categories (since 2006)</li>
  <li>4-Week Positioning Detail — All Trader Categories (Old/Other/All Crop)</li>
  <li>Position Analysis, Trader Count, Position Size charts</li>
  <li>Prod/Merch vs Managed Money (%ile) — 6 scatter charts</li>
  <li>%OI Positioning (%ile) — 6 scatter charts</li>
  <li>Agri Crop COT Executive Summary (Old / Other / All Crop)</li>
  <li>Agri Crop Market Summary (Old / Other / All Crop)</li>
  <li>Agri Crop Weekly Seasonality — 3 charts</li>
</ul>

<p><em>Data source: CFTC Disaggregated Reports (Futures &amp; Options Combined)</em><br>
<em>Generated automatically every Friday after 3:30 PM ET CFTC release.</em></p>

<p style="color:#666;font-size:0.9em;">This is an automated report. Do not reply to this email.</p>
</body></html>
"""

    msg.attach(MIMEText(body, "html"))

    # Attach PDF
    pdf_bytes = PDF_PATH.read_bytes()
    attachment = MIMEBase("application", "pdf")
    attachment.set_payload(pdf_bytes)
    encoders.encode_base64(attachment)
    filename = f"BCOM_COT_{now_et.strftime('%Y%m%d')}.pdf"
    attachment.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(attachment)

    # Send
    print(f"[COT Email] Connecting to {smtp_host}:{smtp_port} ...")
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(email_from, recipients, msg.as_string())

    print(f"[COT Email] Email sent to: {', '.join(recipients)}")
    print(f"[COT Email] PDF size: {len(pdf_bytes)/1024:.1f} KB")


if __name__ == "__main__":
    send()
