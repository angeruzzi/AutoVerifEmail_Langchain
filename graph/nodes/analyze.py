import logging
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from graph.state import EmailAgentState

load_dotenv()

logger = logging.getLogger(__name__)

_SKILL_PATH = Path("skills/email_analysis.md")


@lru_cache(maxsize=1)
def _build_chain():
    """
    Constrói a LangChain chain uma única vez (lazy singleton).

    Estrutura: ChatPromptTemplate | ChatOpenAI | JsonOutputParser
    O sistema usa o conteúdo de skills/email_analysis.md como system prompt.
    As chaves do JSON de exemplo no arquivo são escapadas para que o
    ChatPromptTemplate não as interprete como variáveis de template.
    """
    raw = _SKILL_PATH.read_text(encoding="utf-8")
    # Escapa { e } para evitar que o LangChain trate o JSON de exemplo como variáveis
    system_prompt = raw.replace("{", "{{").replace("}", "}}")

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{email_text}"),
    ])

    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0,  # máxima determinismo para saída JSON consistente
    )

    return prompt | llm | JsonOutputParser()


def _format_email(email: dict) -> str:
    """Formata os campos do e-mail como texto para o LLM."""
    return (
        f"Data: {email.get('date', '')}\n"
        f"De: {email.get('from', '')}\n"
        f"Assunto: {email.get('subject', '')}\n\n"
        f"{email.get('body', '')}"
    )


def analyze_emails(state: EmailAgentState) -> dict:
    """
    Nó 3 — Análise LLM.

    Processa cada e-mail dos chunks atuais com a chain LangChain.
    Acumula resultados em analyzed_emails (não substitui — preserva análises de rodadas anteriores).
    Injeta message_id no resultado para rastreamento de retries no Nó 4.
    Limpa chunks ao final para que o roteador do Nó 4 funcione corretamente.
    """
    chunks = state.get("chunks", [])
    analyzed = list(state.get("analyzed_emails", []))
    errors = list(state.get("errors", []))

    if not chunks:
        logger.info("Nó 3: nenhum chunk para processar")
        return {"analyzed_emails": analyzed, "chunks": [], "errors": errors}

    chain = _build_chain()
    total = sum(len(c) for c in chunks)
    processed = 0

    for chunk in chunks:
        for email in chunk:
            subject = email.get("subject", "?")
            msg_id = email.get("message_id", "")
            try:
                result: dict = chain.invoke({"email_text": _format_email(email)})
                result["message_id"] = msg_id  # adicionado para rastreamento — não vem do LLM
                analyzed.append(result)
                processed += 1
                logger.debug("Analisado: %s", subject)
            except Exception as exc:
                error_msg = f"[Nó 3] Falha na análise de '{subject}' ({msg_id}): {exc}"
                logger.warning(error_msg)
                errors.append(error_msg)

    logger.info("Nó 3: %d/%d e-mail(s) analisado(s)", processed, total)

    return {
        "analyzed_emails": analyzed,
        "chunks": [],   # limpa chunks; Nó 4 repopula se houver retries
        "errors": errors,
    }
