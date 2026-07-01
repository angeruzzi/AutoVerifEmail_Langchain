import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from graph.state import EmailAgentState
from services.gmail_client import fetch_emails

load_dotenv()

logger = logging.getLogger(__name__)

_COLLECTION_WINDOW_HOURS = int(os.getenv("COLLECTION_WINDOW_HOURS", "24"))
_LAST_RUN_PATH = Path("last_run.json")


def _read_last_run() -> datetime | None:
    """Retorna o timestamp da última execução bem-sucedida, ou None se ausente/inválido."""
    if not _LAST_RUN_PATH.exists():
        return None
    try:
        data = json.loads(_LAST_RUN_PATH.read_text(encoding="utf-8"))
        return datetime.fromisoformat(data["last_run"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("last_run.json inválido, usando fallback: %s", exc)
        return None


def collect_emails(state: EmailAgentState) -> dict:
    """
    Nó 1 — Coleta Gmail.

    Determina o limite inferior da janela de coleta:
    - last_run.json presente  → usa o timestamp salvo
    - last_run.json ausente   → usa agora − COLLECTION_WINDOW_HOURS (primeira execução)

    Inicializa todos os campos do estado para evitar KeyError nos nós seguintes.
    """
    last_run = _read_last_run()

    if last_run is None:
        since = datetime.now(tz=timezone.utc) - timedelta(hours=_COLLECTION_WINDOW_HOURS)
        logger.info("Primeira execução — coletando últimas %dh", _COLLECTION_WINDOW_HOURS)
    else:
        since = last_run
        logger.info("Coletando e-mails desde %s", since.isoformat())

    raw_emails = fetch_emails(since=since)
    logger.info("Nó 1: %d e-mail(s) coletado(s)", len(raw_emails))

    return {
        "raw_emails": raw_emails,
        "chunks": [],
        "analyzed_emails": [],
        "invalid_emails": [],
        "filtered_emails": [],
        "critical_emails": [],
        "digest_messages": [],
        "summary": "",
        "retry_counts": {},
        "errors": [],
    }
