import logging
import os

from dotenv import load_dotenv

from graph.state import EmailAgentState

load_dotenv()

logger = logging.getLogger(__name__)

_CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "10"))


def chunk_emails(state: EmailAgentState) -> dict:
    """
    Nó 2 — Chunking.

    Divide raw_emails em lotes de CHUNK_SIZE para processamento pelo LLM.
    Lotes menores reduzem o risco de timeout e facilitam o retry individual (Nó 4).
    """
    raw_emails = state["raw_emails"]

    if not raw_emails:
        logger.info("Nó 2: nenhum e-mail para chunkar")
        return {"chunks": []}

    chunks = [
        raw_emails[i : i + _CHUNK_SIZE]
        for i in range(0, len(raw_emails), _CHUNK_SIZE)
    ]

    logger.info(
        "Nó 2: %d e-mail(s) dividido(s) em %d chunk(s) de até %d",
        len(raw_emails),
        len(chunks),
        _CHUNK_SIZE,
    )

    return {"chunks": chunks}
