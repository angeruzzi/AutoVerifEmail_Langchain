import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_EVOLUTION_URL = os.getenv("EVOLUTION_URL", "http://localhost:8080")
_EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
_EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "")
_WHATSAPP_TARGET_NUMBER = os.getenv("WHATSAPP_TARGET_NUMBER", "")


def send_text(message: str) -> None:
    """
    Envia uma mensagem de texto via Evolution API.

    Endpoint: POST /message/sendText/{instance}
    Compatível com Evolution API v2.
    """
    url = f"{_EVOLUTION_URL}/message/sendText/{_EVOLUTION_INSTANCE}"
    headers = {
        "apikey": _EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "number": _WHATSAPP_TARGET_NUMBER,
        "text": message,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()

    logger.info("Mensagem enviada via WhatsApp (%d chars)", len(message))


def send_all(messages: list[str]) -> None:
    """Envia lista de mensagens sequencialmente via Evolution API."""
    for i, msg in enumerate(messages, 1):
        logger.info("Enviando mensagem WhatsApp %d/%d", i, len(messages))
        send_text(msg)
