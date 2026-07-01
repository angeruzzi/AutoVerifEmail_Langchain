from typing import TypedDict


class EmailAgentState(TypedDict):
    raw_emails: list[dict]       # e-mails brutos coletados do Gmail
    chunks: list[list[dict]]     # lotes para análise (também usados em retries)
    analyzed_emails: list[dict]  # JSONs analisados pelo LLM
    invalid_emails: list[dict]   # e-mails que esgotaram retries sem JSON válido
    filtered_emails: list[dict]  # e-mails após filtros configuráveis
    critical_emails: list[dict]  # subconjunto com priority == CRITICAL
    digest_messages: list[str]   # strings formatadas para envio via WhatsApp
    summary: str                 # frase de contexto geral gerada pelo LLM
    retry_counts: dict[str, int] # chave: id do e-mail (Gmail message_id)
    errors: list[str]            # erros não fatais registrados durante a execução
