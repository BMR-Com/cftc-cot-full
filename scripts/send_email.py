"""
send_email.py
Sends the generated COT report PDF via email using SMTP.

Requirements: Set environment variables for SMTP credentials
"""

import os
import sys
from pathlib import Path
from email.message import EmailMessage
from email.utils import formatdate
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
# Use raw ASCII-only strings to avoid any hidden Unicode characters
EMAIL_SUBJECT = "BCOM COT Weekly Report"
EMAIL_BODY = """BCOM COT Weekly Report

Please find attached the latest CFTC Commitment of Traders report for Bloomberg Commodity Index constituents.

Report generated automatically from CFTC public data.

---
This is an automated email. Please do not reply.
"""


def clean_string(s):
    """Remove any non-ASCII characters to avoid encoding issues."""
    return s.encode('ascii', 'ignore').decode('ascii')


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
    
    # Create the email message using modern EmailMessage API [^69^][^75^][^77^]
    msg = EmailMessage()
    msg['From'] = clean_string(EMAIL_FROM)
    msg['To'] = clean_string(", ".join(recipients))
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = clean_string(EMAIL_SUBJECT)
    
    # Set content with explicit UTF-8 encoding [^74^][^75^]
    # EmailMessage handles encoding automatically
    msg.set_content(clean_string(EMAIL_BODY))
    
    # Attach the PDF file [^69^][^75^][^77^]
    print(f"[COT Email] Attaching PDF: {PDF_FILE.name}")
    with open(PDF_FILE, "rb") as f:
        pdf_data = f.read()
    
    # Use add_attachment with proper MIME type [^72^][^77^]
    msg.add_attachment(
        pdf_data,
        maintype='application',
        subtype='pdf',
        filename=PDF_FILE.name
    )
    
    # Send the email
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        
        print(f"[COT Email] Sending to {len(recipients)} recipient(s) ...")
        
        # Use send_message() which handles EmailMessage properly [^69^][^75^][^77^]
        server.send_message(msg, EMAIL_FROM, recipients)
        
        print(f"[COT Email] Successfully sent to: {', '.join(recipients)}")
        server.quit()
        
    except Exception as e:
        print(f"[COT Email] ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    send()
