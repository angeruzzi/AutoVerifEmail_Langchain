import logging
import os

from dotenv import load_dotenv

from graph.state import EmailAgentState

load_dotenv()

logger = logging.getLogger(__name__)

_MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.5"))
_MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
_VALID_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def _validate(email: dict) -> tuple[bool, str]:
    """Valida campos obrigatórios, confidence e priority. Retorna (válido, motivo)."""
    for field in ("summary", "categories", "priority", "confidence"):
        if field not in email or email[field] is None:
            return False, f"campo obrigatório ausente ou nulo: '{field}'"

    if not isinstance(email["categories"], list) or len(email["categories"]) == 0:
        return False, "categories deve ser lista não vazia"

    if email["priority"] not in _VALID_PRIORITIES:
        return False, f"priority inválida: '{email['priority']}'"

    confidence = email["confidence"]
    if not isinstance(confidence, (int, float)) or confidence < _MIN_CONFIDENCE:
        return False, f"confidence {confidence} abaixo do mínimo {_MIN_CONFIDENCE}"

    return True, ""


def validate_emails(state: EmailAgentState) -> dict:
    """
    Nó 4 — Validação de qualidade.

    Para cada e-mail em analyzed_emails:
    - Válido → permanece em analyzed_emails
    - Inválido com retries disponíveis → volta ao Nó 3 como chunk de 1 e-mail (raw)
    - Inválido sem retries → move para invalid_emails

    O roteador do Nó 4 em graph_builder verifica se chunks está não vazio
    para decidir se retorna ao Nó 3 ou avança ao Nó 5.
    Chunks de retry usam o e-mail raw original (de raw_emails), não o resultado do LLM.
    """
    analyzed = list(state.get("analyzed_emails", []))
    raw_emails = state.get("raw_emails", [])
    retry_counts = dict(state.get("retry_counts", {}))
    invalid_emails = list(state.get("invalid_emails", []))
    errors = list(state.get("errors", []))

    raw_by_id = {e["message_id"]: e for e in raw_emails}

    valid: list[dict] = []
    retry_chunks: list[list[dict]] = []

    for email in analyzed:
        is_valid, reason = _validate(email)
        if is_valid:
            valid.append(email)
            continue

        msg_id = email.get("message_id", "")
        subject = email.get("subject", "?")
        current = retry_counts.get(msg_id, 0)

        if current < _MAX_RETRIES:
            retry_counts[msg_id] = current + 1
            original = raw_by_id.get(msg_id)
            if original:
                retry_chunks.append([original])  # chunk de 1 — re-análise individual
                logger.warning(
                    "Nó 4: '%s' inválido (%s) — retry %d/%d",
                    subject, reason, current + 1, _MAX_RETRIES,
                )
            else:
                # message_id não encontrado em raw_emails — descarta sem retry
                error_msg = f"[Nó 4] Raw email não encontrado para retry (id={msg_id})"
                errors.append(error_msg)
                invalid_emails.append(email)
        else:
            error_msg = (
                f"[Nó 4] '{subject}' (id={msg_id}) esgotou {_MAX_RETRIES} retries: {reason}"
            )
            errors.append(error_msg)
            invalid_emails.append(email)
            logger.error("Nó 4: %s", error_msg)

    logger.info(
        "Nó 4: %d válido(s), %d para retry, %d inválido(s) definitivo(s)",
        len(valid), len(retry_chunks), len(invalid_emails),
    )

    return {
        "analyzed_emails": valid,
        "chunks": retry_chunks,   # não vazio → roteador volta ao Nó 3
        "retry_counts": retry_counts,
        "invalid_emails": invalid_emails,
        "errors": errors,
    }
