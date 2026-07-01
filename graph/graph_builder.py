from langgraph.graph import StateGraph, END

from graph.state import EmailAgentState
from graph.nodes.collect import collect_emails
from graph.nodes.chunk import chunk_emails
from graph.nodes.analyze import analyze_emails
from graph.nodes.validate import validate_emails
from graph.nodes.filter_route import filter_and_route
from graph.nodes.alert import send_critical_alert
from graph.nodes.format_digest import format_digest
from graph.nodes.summarize import summarize_day
from graph.nodes.send import send_messages


def _route_after_validation(state: EmailAgentState) -> str:
    """Nó 4 → Nó 3 se ainda há chunks de retry; caso contrário → Nó 5."""
    if state.get("chunks"):
        return "analyze"
    return "filter_route"


def _route_after_filter(state: EmailAgentState) -> str:
    """Nó 5 → Nó 8 direto se não há e-mails relevantes; caso contrário → Nó 6a."""
    if not state.get("filtered_emails"):
        return "send"
    return "alert"


def build_graph():
    graph = StateGraph(EmailAgentState)

    graph.add_node("collect", collect_emails)
    graph.add_node("chunk", chunk_emails)
    graph.add_node("analyze", analyze_emails)
    graph.add_node("validate", validate_emails)
    graph.add_node("filter_route", filter_and_route)
    graph.add_node("alert", send_critical_alert)
    graph.add_node("format_digest", format_digest)
    graph.add_node("summarize", summarize_day)
    graph.add_node("send", send_messages)

    graph.set_entry_point("collect")
    graph.add_edge("collect", "chunk")
    graph.add_edge("chunk", "analyze")
    graph.add_edge("analyze", "validate")

    # Nó 4 → retry (Nó 3) ou Nó 5
    graph.add_conditional_edges(
        "validate",
        _route_after_validation,
        {"analyze": "analyze", "filter_route": "filter_route"},
    )

    # Nó 5 → Nó 8 (sem e-mails) ou Nó 6a → 6b → 7 → 8
    graph.add_conditional_edges(
        "filter_route",
        _route_after_filter,
        {"send": "send", "alert": "alert"},
    )

    graph.add_edge("alert", "format_digest")
    graph.add_edge("format_digest", "summarize")
    graph.add_edge("summarize", "send")
    graph.add_edge("send", END)

    return graph.compile()
