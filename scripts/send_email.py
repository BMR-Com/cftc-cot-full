"""
send_email.py
Sends the generated COT report PDF via email using SMTP.
"""

import os
import sys
from pathlib import Path
from email.message import EmailMessage
from email.utils import formatdate
import smtplib

PDF_FILE = Path(__file__).parent.parent / "cot_report.pdf"

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

EMAIL_SUBJECT = "BCOM COT Weekly Report - Tullett Prebon Agriculture"
EMAIL_BODY = """Tullett Prebon Agriculture
BCOM COT Weekly Report

Please find attached the latest CFTC Commitment of Traders report for Bloomberg Commodity Index constituents.

Report generated automatically from CFTC public data.

---
This is an automated email. Please do not reply.
"""


def send():
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO]):
        print("ERROR: Missing email configuration.")
        sys.exit(1)
    
    if not PDF_FILE.exists():
        print(f"ERROR: PDF file not found at {PDF_FILE}")
        sys.exit(1)
    
    recipients = [email.strip() for email in EMAIL_TO.split(",") if email.strip()]
    if not recipients:
        print("ERROR: No valid recipients found")
        sys.exit(1)
    
    print(f"[COT Email] Connecting to {SMTP_HOST}:{SMTP_PORT} ...")
    
    msg = EmailMessage()
    msg['From'] = EMAIL_FROM
    msg['To'] = ", ".join(recipients)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = EMAIL_SUBJECT
    
    msg.set_content(EMAIL_BODY)
    
    print(f"[COT Email] Attaching PDF: {PDF_FILE.name} ({PDF_FILE.stat().st_size/1024:.1f} KB)")
    with open(PDF_FILE, "rb") as f:
        pdf_data = f.read()
    
    msg.add_attachment(
        pdf_data,
        maintype='application',
        subtype='pdf',
        filename=PDF_FILE.name
    )
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg, EMAIL_FROM, recipients)
        
        print(f"[COT Email] Successfully sent to {len(recipients)} recipient(s)")
        
    except Exception as e:
        print(f"[COT Email] ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    send()
