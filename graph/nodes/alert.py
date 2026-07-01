import logging

from graph.state import EmailAgentState

logger = logging.getLogger(__name__)

_HEADER = "🚨 ALERTA CRÍTICO 🚨"
_DIVIDER = "━" * 30


def _format_critical(email: dict) -> str:
    """Formata mensagem de alerta para um e-mail CRITICAL."""
    lines = [
        _HEADER,
        _DIVIDER,
        f"De: {email.get('from', '?')}",
        f"Assunto: {email.get('subject', '?')}",
        f"Data: {email.get('date', '?')}",
        "",
        f"📋 Resumo:\n{email.get('summary', '—')}",
    ]

    if email.get("suggested_action"):
        lines += ["", f"⚡ Ação necessária:\n{email['suggested_action']}"]

    if email.get("deadline"):
        lines += ["", f"⏰ Prazo: {email['deadline']}"]

    if email.get("reasoning"):
        lines += ["", f"💭 Motivo: {email['reasoning']}"]

    lines.append(_DIVIDER)
    return "\n".join(lines)


def send_critical_alert(state: EmailAgentState) -> dict:
    """
    Nó 6a — Alerta imediato.

    Formata uma mensagem de alerta para cada e-mail em critical_emails
    e as insere no início de digest_messages (enviadas antes do digest regular).
    É no-op se critical_emails estiver vazio.
    """
    critical = state.get("critical_emails", [])
    existing = list(state.get("digest_messages", []))

    if not critical:
        logger.info("Nó 6a: nenhum e-mail crítico")
        return {}

    alerts = [_format_critical(e) for e in critical]
    logger.info("Nó 6a: %d alerta(s) crítico(s) formatado(s)", len(alerts))

    # Alertas ficam no início — são enviados antes do digest regular
    return {"digest_messages": alerts + existing}
