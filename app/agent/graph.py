import time
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import AgentState


def _after_guard(state: AgentState) -> str:
    return "blocked" if state.get("blocked") else "route"


def _route_tool(state: AgentState) -> str:
    return "policy_search" if state.get("route") == "policy" else "answer"


def _after_citation(state: AgentState) -> str:
    return "retry" if state.get("citation_ok") is False else "end"


@lru_cache(maxsize=1)
def get_graph():
    graph = StateGraph(AgentState)

    graph.add_node("guard", nodes.guard_node)
    graph.add_node("route", nodes.route_node)
    graph.add_node("policy_search", nodes.policy_search_node)
    graph.add_node("answer", nodes.answer_node)
    graph.add_node("citation_check", nodes.citation_check_node)

    graph.add_edge(START, "guard")
    graph.add_conditional_edges("guard", _after_guard, {"blocked": END, "route": "route"})
    graph.add_conditional_edges(
        "route",
        _route_tool,
        {"policy_search": "policy_search", "answer": "answer"},
    )
    graph.add_edge("policy_search", "answer")
    graph.add_edge("answer", "citation_check")
    graph.add_conditional_edges("citation_check", _after_citation, {"retry": "answer", "end": END})

    return graph.compile()


def run_agent(*, question: str, username: str, role: str, full_name: str, ip: str = "") -> dict:
    """Execute the full agent workflow and return a response payload."""
    started = time.perf_counter()
    initial: AgentState = {
        "question": question.strip(),
        "username": username,
        "role": role,
        "full_name": full_name,
        "ip": ip,
        "trace": [],
        "attempts": 0,
        "blocked": False,
    }
    final = get_graph().invoke(initial)
    latency_ms = int((time.perf_counter() - started) * 1000)

    blocked = bool(final.get("blocked"))
    if blocked:
        answer = final.get("refusal") or "This request was blocked."
        route = "blocked"
    else:
        answer = final.get("answer") or "I couldn't produce an answer for that."
        route = final.get("route") or "policy"

    return {
        "answer": answer,
        "blocked": blocked,
        "route": route,
        "guard_reason": final.get("guard_reason"),
        "citations": final.get("citations") or [],
        "trace": final.get("trace") or [],
        "latency_ms": latency_ms,
    }
