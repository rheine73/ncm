import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText

import requests

from .settings import Settings


def send_telegram(settings: Settings, message: str) -> bool:
    if not settings.telegram_token or not settings.telegram_chat_id:
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
    payload = {"chat_id": settings.telegram_chat_id, "text": message}
    try:
        r = requests.post(url, json=payload, timeout=20)
        r.raise_for_status()
        return True
    except Exception:
        return False


def send_email(settings: Settings, subject: str, message: str) -> bool:
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.smtp_from, settings.smtp_to]):
        return False

    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = settings.smtp_to

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls(context=context)
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        return False


def save_email_preview(settings: Settings, subject: str, message: str) -> str | None:
    if not message.strip():
        return None

    out_dir = settings.logs_dir / "email_outbox"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"email_preview_{ts}.txt"

    body = (
        f"generated_at={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"subject={subject}\n"
        f"from={settings.smtp_from}\n"
        f"to={settings.smtp_to}\n"
        "\n"
        f"{message}\n"
    )
    out_path.write_text(body, encoding="utf-8")
    return str(out_path)


def dispatch_alerts(settings: Settings, lines: list[str]) -> dict:
    payload = "\n".join(lines).strip()
    if not payload:
        return {"telegram": False, "email": False, "preview_file": None}

    subject = "Monitor Fiscal - Novos alertas"
    preview_file = save_email_preview(settings, subject, payload)

    if not settings.enable_alerts:
        return {"telegram": False, "email": False, "preview_file": preview_file}

    return {
        "telegram": send_telegram(settings, payload),
        "email": send_email(settings, subject, payload),
        "preview_file": preview_file,
    }
