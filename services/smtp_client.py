import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USER = os.getenv("SMTP_USER", "")
_SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
_FALLBACK_EMAIL_TO = os.getenv("FALLBACK_EMAIL_TO", "")


def send_email(subject: str, body: str) -> None:
    """Envia e-mail via SMTP com STARTTLS (fallback do WhatsApp)."""
    msg = MIMEMultipart()
    msg["From"] = _SMTP_USER
    msg["To"] = _FALLBACK_EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
        server.starttls()
        server.login(_SMTP_USER, _SMTP_PASSWORD)
        server.sendmail(_SMTP_USER, [_FALLBACK_EMAIL_TO], msg.as_string())

    logger.info("E-mail enviado via SMTP para %s", _FALLBACK_EMAIL_TO)


def send_all(subject: str, messages: list[str]) -> None:
    """Concatena lista de mensagens e envia como um único e-mail (fallback)."""
    body = "\n\n" + ("-" * 60 + "\n\n").join(messages)
    send_email(subject, body)
