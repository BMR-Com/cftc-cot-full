"""
send_email.py
Sends the generated COT report PDF via email using SMTP.

Requirements: Set environment variables for SMTP credentials
"""

import os
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
import smtplib

# ── Config ─────────────────────────────────────────────────────────────────
PDF_FILE = Path(__file__).parent.parent / "cot_report.pdf"

# Email configuration from environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

# ── Email content ───────────────────────────────────────────────────────────
EMAIL_SUBJECT = "BCOM COT Weekly Report"
EMAIL_BODY = """BCOM COT Weekly Report

Please find attached the latest CFTC Commitment of Traders report for Bloomberg Commodity Index constituents.

Report generated automatically from CFTC public data.

---
This is an automated email. Please do not reply.
"""


def send():
    """Send the PDF report via email."""
    
    # Validate configuration
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO]):
        print("ERROR: Missing email configuration. Check environment variables:")
        print("  SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO")
        sys.exit(1)
    
    if not PDF_FILE.exists():
        print(f"ERROR: PDF file not found at {PDF_FILE}")
        sys.exit(1)
    
    # Parse recipients (comma-separated)
    recipients = [email.strip() for email in EMAIL_TO.split(",") if email.strip()]
    if not recipients:
        print("ERROR: No valid recipients found in EMAIL_TO")
        sys.exit(1)
    
    print(f"[COT Email] Connecting to {SMTP_HOST}:{SMTP_PORT} ...")
    
    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = ", ".join(recipients)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = EMAIL_SUBJECT
    
    # Attach the email body with proper UTF-8 encoding [^49^]
    # Use MIMEText with _charset='utf-8' to handle Unicode properly
    body_part = MIMEText(EMAIL_BODY, 'plain', _charset='utf-8')
    msg.attach(body_part)
    
    # Attach the PDF file
    print(f"[COT Email] Attaching PDF: {PDF_FILE.name}")
    with open(PDF_FILE, "rb") as f:
        pdf_part = MIMEBase("application", "octet-stream")
        pdf_part.set_payload(f.read())
    
    encoders.encode_base64(pdf_part)
    pdf_part.add_header(
        "Content-Disposition",
        f"attachment; filename={PDF_FILE.name}",
    )
    msg.attach(pdf_part)
    
    # Send the email
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        
        print(f"[COT Email] Sending to {len(recipients)} recipient(s) ...")
        
        # ── FIX: Use send_message() instead of sendmail() for proper UTF-8 handling [^37^][^39^][^41^]
        # send_message() properly handles email.message.Message objects and encodes them correctly
        # sendmail() expects ASCII strings and fails with Unicode characters
        server.send_message(msg, EMAIL_FROM, recipients)
        
        print(f"[COT Email] Successfully sent to: {', '.join(recipients)}")
        server.quit()
        
    except Exception as e:
        print(f"[COT Email] ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    send()
