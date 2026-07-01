import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from graph.state import EmailAgentState

load_dotenv()

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Você é um assistente de triagem de e-mails.\n"
    "Com base na lista de e-mails abaixo (assunto e prioridade), gere UMA ÚNICA frase "
    "curta e objetiva resumindo o contexto do dia para o usuário.\n"
    "Exemplo: \"Você tem 2 e-mails urgentes sobre pagamento e 1 convite de reunião.\"\n"
    "Responda APENAS com a frase. Sem markdown, sem pontuação extra."
)


@lru_cache(maxsize=1)
def _build_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", "{email_list}"),
    ])
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0.3,  # leve criatividade para linguagem natural fluída
    )
    return prompt | llm | StrOutputParser()


def _build_email_list(emails: list[dict]) -> str:
    """Formata assuntos e prioridades como lista numerada para o LLM."""
    lines = [
        f"{i}. [{e.get('priority', 'LOW')}] {e.get('subject', '?')}"
        for i, e in enumerate(emails, 1)
    ]
    return "\n".join(lines)


def summarize_day(state: EmailAgentState) -> dict:
    """
    Nó 7 — Sumarização do dia.

    Invoca o LLM com a lista de assuntos e prioridades de filtered_emails
    e gera uma frase curta de contexto geral do dia.
    Insere a frase como primeira mensagem em digest_messages
    (antes dos alertas críticos e do digest regular).
    """
    filtered = state.get("filtered_emails", [])
    existing = list(state.get("digest_messages", []))

    if not filtered:
        logger.info("Nó 7: nenhum e-mail filtrado — sem sumarização")
        return {}

    try:
        email_list = _build_email_list(filtered)
        chain = _build_chain()
        summary = chain.invoke({"email_list": email_list}).strip()
        logger.info("Nó 7: resumo gerado — '%s'", summary)
    except Exception as exc:
        summary = f"Você tem {len(filtered)} e-mail(s) relevante(s) no período."
        logger.warning("Nó 7: falha na sumarização LLM, usando fallback: %s", exc)

    return {
        "summary": summary,
        "digest_messages": [summary] + existing,  # inserido como primeira mensagem
    }
