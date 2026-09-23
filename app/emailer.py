"""
Minimal email-sending helper used for registration verification.
 
If BUGBOUNTY_SMTP_HOST is configured (see app/config.py), a real email is
sent over SMTP. Otherwise, the message is printed to the server console —
this keeps local development and testing working without requiring a real
mailbox, while still exercising the full verification flow end-to-end.
"""
 
import smtplib
from email.message import EmailMessage
 
from app.config import settings
 
 
def _console_fallback(to_email: str, subject: str, body: str) -> None:
    print(
        "\n"
        "==================== [dev] EMAIL NOT SENT (no SMTP configured) ====================\n"
        f"To:      {to_email}\n"
        f"Subject: {subject}\n"
        "-------------------------------------------------------------------------------------\n"
        f"{body}\n"
        "=======================================================================================\n"
    )
 
 
def send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        _console_fallback(to_email, subject, body)
        return
 
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body)
 
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as exc:  # noqa: BLE001 - never let email failures break registration
        print(f"[emailer] Failed to send email to {to_email}: {exc}")
        _console_fallback(to_email, subject, body)
 
 
def send_verification_email(to_email: str, username: str, token: str) -> None:
    verify_url = f"{settings.FRONTEND_BASE_URL}/?verify_token={token}"
    subject = "Verify your BugCasp account"
    body = (
        f"Hi {username},\n\n"
        "Thanks for registering on BugCasp. Please verify your email address "
        f"by clicking the link below (valid for {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours):\n\n"
        f"{verify_url}\n\n"
        "If you didn't create this account, you can ignore this email.\n"
    )
    send_email(to_email, subject, body)
 