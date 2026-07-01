import logging
import os

from dotenv import load_dotenv

from graph.state import EmailAgentState

load_dotenv()

logger = logging.getLogger(__name__)

_PRIORITY_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "⚪"}
_PRIORITY_SORT = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
_SEPARATOR = "\n\n"


def _format_entry(email: dict) -> str:
    """Formata um único e-mail como bloco de texto para WhatsApp."""
    priority = (email.get("priority") or "LOW").upper()
    emoji = _PRIORITY_EMOJI.get(priority, "⚪")

    lines = [
        f"{emoji} {email.get('subject', '?')}",
        f"De: {email.get('from', '?')}",
        email.get("summary") or "",
    ]

    if email.get("requires_action") and email.get("suggested_action"):
        lines.append(f"⚡ Ação: {email['suggested_action']}")

    if email.get("deadline"):
        lines.append(f"⏰ Prazo: {email['deadline']}")

    return "\n".join(filter(None, lines))


def _pack(entries: list[str], max_chars: int) -> list[str]:
    """
    Empacota blocos de texto em mensagens de no máximo max_chars chars.
    Garante que nenhuma mensagem individual ultrapasse o limite do WhatsApp.
    """
    messages: list[str] = []
    parts: list[str] = []
    length = 0

    for entry in entries:
        sep_len = len(_SEPARATOR) if parts else 0
        needed = len(entry) + sep_len

        if parts and length + needed > max_chars:
            messages.append(_SEPARATOR.join(parts))
            parts = [entry]
            length = len(entry)
        else:
            parts.append(entry)
            length += needed

    if parts:
        messages.append(_SEPARATOR.join(parts))

    return messages


def format_digest(state: EmailAgentState) -> dict:
    """
    Nó 6b — Formata digest.

    Ordena filtered_emails por prioridade (CRITICAL → HIGH → MEDIUM → LOW),
    formata cada um como bloco de texto com emoji, assunto, remetente, resumo,
    ação sugerida (se requires_action) e prazo (se deadline).
    Quebra em múltiplas mensagens se necessário (≤ WHATSAPP_MAX_CHARS).
    Acumula em digest_messages sem sobrescrever alertas do Nó 6a.
    """
    filtered = state.get("filtered_emails", [])
    existing = list(state.get("digest_messages", []))
    max_chars = int(os.getenv("WHATSAPP_MAX_CHARS", "4096"))

    sorted_emails = sorted(
        filtered,
        key=lambda e: _PRIORITY_SORT.get((e.get("priority") or "LOW").upper(), 3),
    )

    entries = [_format_entry(e) for e in sorted_emails]
    new_messages = _pack(entries, max_chars)

    logger.info(
        "Nó 6b: %d e-mail(s) formatado(s) → %d mensagem(ns)",
        len(filtered),
        len(new_messages),
    )

    return {"digest_messages": existing + new_messages}
