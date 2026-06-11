"""Email sending for password reset. Uses env vars for SMTP (no hardcoded credentials)."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional


def send_password_reset_email(to_email: str, reset_link: str) -> Optional[str]:
    """
    Send a password reset email with the given link.

    Config via environment variables:
        SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
        SMTP_FROM (sender address), SMTP_USE_TLS (default true).

    Returns:
        None on success, or an error message string on failure.
    """
    host = os.environ.get("SMTP_HOST")
    if not host:
        return "SMTP not configured (set SMTP_HOST and related env vars)."
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    from_addr = os.environ.get("SMTP_FROM") or user
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    subject = "Fuel Requisition System – Password Reset"
    body = f"""Hello,

You requested a password reset for the Fuel Requisition System.

Click the link below to set a new password (link expires in 1 hour):

{reset_link}

If you did not request this, please ignore this email.

—
Fuel Requisition System
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))

    try:
        # Port 465 uses implicit SSL (SMTP_SSL); 587 uses STARTTLS
        if port == 465:
            with smtplib.SMTP_SSL(host, port) as server:
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port) as server:
                if use_tls:
                    server.starttls()
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [to_email], msg.as_string())
        return None
    except Exception as e:
        return str(e)
