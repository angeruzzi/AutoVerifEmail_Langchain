import logging
import os

from dotenv import load_dotenv

from graph.state import EmailAgentState

load_dotenv()

logger = logging.getLogger(__name__)

_PRIORITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _parse_env_filters() -> tuple[set[str], int, bool, bool]:
    """Lê e normaliza os filtros do .env uma vez por execução do nó."""
    excluded = {
        c.strip().upper()
        for c in os.getenv("FILTER_CATEGORIES", "").split(",")
        if c.strip()
    }
    min_priority = _PRIORITY_ORDER.get(
        os.getenv("FILTER_MIN_PRIORITY", "LOW").upper(), 0
    )
    req_action = os.getenv("FILTER_REQUIRES_ACTION", "false").lower() == "true"
    req_response = os.getenv("FILTER_REQUIRES_RESPONSE", "false").lower() == "true"
    return excluded, min_priority, req_action, req_response


def _passes(email: dict, excluded: set[str], min_priority: int,
            req_action: bool, req_response: bool) -> bool:
    """Retorna True se o e-mail passa em todos os filtros (AND cumulativo)."""
    cats = set(email.get("categories") or [])
    if cats & excluded:
        return False

    priority_val = _PRIORITY_ORDER.get((email.get("priority") or "LOW").upper(), 0)
    if priority_val < min_priority:
        return False

    if req_action and not email.get("requires_action"):
        return False

    if req_response and not email.get("requires_response"):
        return False

    return True


def filter_and_route(state: EmailAgentState) -> dict:
    """
    Nó 5 — Filtro + Roteador.

    Aplica filtros cumulativos (AND) sobre analyzed_emails.
    Separa critical_emails do conjunto filtrado.
    Se nenhum e-mail passou: preenche digest_messages com aviso padrão
    para que o roteador encaminhe direto ao Nó 8.
    """
    analyzed = state.get("analyzed_emails", [])
    excluded, min_priority, req_action, req_response = _parse_env_filters()

    filtered = [
        e for e in analyzed
        if _passes(e, excluded, min_priority, req_action, req_response)
    ]
    critical = [e for e in filtered if (e.get("priority") or "").upper() == "CRITICAL"]

    logger.info(
        "Nó 5: %d/%d e-mail(s) após filtros (%d crítico(s))",
        len(filtered), len(analyzed), len(critical),
    )

    if not filtered:
        logger.info("Nó 5: nenhum e-mail relevante — roteando para envio direto")
        return {
            "filtered_emails": [],
            "critical_emails": [],
            "digest_messages": ["Nenhum e-mail relevante no período analisado."],
        }

    return {
        "filtered_emails": filtered,
        "critical_emails": critical,
        "digest_messages": [],
    }
