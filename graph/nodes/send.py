import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from graph.state import EmailAgentState
from services import evolution_client, smtp_client

logger = logging.getLogger(__name__)

_LAST_RUN_PATH = Path("last_run.json")
_SMTP_SUBJECT = "Digest de E-mails"


def _write_last_run() -> None:
    """Grava o timestamp da execução bem-sucedida em last_run.json."""
    data = {"last_run": datetime.now(tz=timezone.utc).isoformat()}
    _LAST_RUN_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("last_run.json atualizado: %s", data["last_run"])


def _append_warning(messages: list[str], errors: list[str], invalid: list[dict]) -> list[str]:
    """Adiciona aviso de erros/inválidos ao final da última mensagem."""
    if not errors and not invalid:
        return messages

    parts = []
    if invalid:
        parts.append(f"⚠️ {len(invalid)} e-mail(s) não puderam ser analisados após retries.")
    if errors:
        parts.append(f"⚠️ {len(errors)} erro(s) registrado(s) durante a execução.")

    warning = "\n".join(parts)
    result = list(messages)

    if result:
        result[-1] = result[-1] + "\n\n" + warning
    else:
        result = [warning]

    return result


def send_messages(state: EmailAgentState) -> dict:
    """
    Nó 8 — Envio.

    Envia cada mensagem em digest_messages via Evolution API (WhatsApp).
    Fallback por mensagem: se WhatsApp falhar, tenta SMTP.
    Se ambos falharem: registra erro crítico no log (sem lançar exceção).
    Grava last_run.json apenas se ao menos uma mensagem foi entregue com sucesso.
    """
    messages = list(state.get("digest_messages", []))
    errors = list(state.get("errors", []))
    invalid = list(state.get("invalid_emails", []))

    messages = _append_warning(messages, errors, invalid)

    if not messages:
        logger.info("Nó 8: nenhuma mensagem para enviar")
        _write_last_run()
        return {}

    total = len(messages)
    any_success = False

    for i, msg in enumerate(messages, 1):
        logger.info("Nó 8: enviando mensagem %d/%d", i, total)
        try:
            evolution_client.send_text(msg)
            any_success = True
        except Exception as wa_exc:
            logger.warning("WhatsApp falhou (msg %d/%d): %s — tentando SMTP", i, total, wa_exc)
            try:
                smtp_client.send_email(_SMTP_SUBJECT, msg)
                any_success = True
                logger.info("Mensagem %d/%d entregue via SMTP (fallback)", i, total)
            except Exception as smtp_exc:
                logger.error(
                    "Falha em ambos os canais (msg %d/%d) — WA: %s | SMTP: %s",
                    i, total, wa_exc, smtp_exc,
                )

    if any_success:
        _write_last_run()
    else:
        logger.critical(
            "Nó 8: nenhuma mensagem foi entregue — last_run.json NÃO atualizado"
        )

    return {}
