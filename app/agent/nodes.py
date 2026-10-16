"""LangGraph nodes: guard -> route -> policy_search -> answer -> citation_check."""

import logging
import re
import time

from ..audit import log_event
from ..config import get_settings
from ..db import SessionLocal
from ..policies import load_policy_index
from ..security import ROLE_ADMIN, ROLE_HR
from . import prompts
from .llm import chat as llm_chat
from .llm import llm_active
from .retriever import search_policies

log = logging.getLogger(__name__)

# --------------------------------------------------------------------- guard
INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|prompts?|directions?)", "prompt_injection"),
    (r"disregard\s+(your\s+|all\s+|the\s+)?(instructions?|rules?|prompts?|system)", "prompt_injection"),
    (r"(reveal|show|print|display|repeat|output|dump)\s+(me\s+)?(your\s+|the\s+)?(system\s+prompt|instructions|hidden\s+rules|internal\s+prompt)", "prompt_injection"),
    (r"jailbreak|do\s+anything\s+now", "prompt_injection"),
    (r"(bypass|ignore|override|circumvent)\s+(the\s+)?(access|permission|restriction|rbac|role|security|guard)", "prompt_injection"),
]

SECRET_PATTERNS = [
    r"what('s|\s+is|\s+are)\s+(the\s+|your\s+)?(jwt|api[\s_-]?key|secret|password|credential|token|hash)\b(?!\s+polic)",
    r"(tell|give|show)\s+(me\s+)?(the\s+)?(jwt\s+secret|api[\s_-]?key|secret\s+key|access\s+token|password\s+hash)\b",
    r"(password|credential|token|hash|secret)\s+(for|of)\s+[a-z]",
]

IMPERSONATION_RE = re.compile(
    r"(?:i\s*am|i'?m|act\s+as|as)\s+(?:an?\s+|the\s+)?(admin|administrator|hr|human\s+resources)\b",
    re.IGNORECASE,
)
_CLAIMED_ROLE = {"admin": ROLE_ADMIN, "administrator": ROLE_ADMIN, "hr": ROLE_HR, "human resources": ROLE_HR}

REFUSALS = {
    "prompt_injection": "I can't follow instructions that try to change how I work. I can only answer questions about the policy documents available to your role.",
    "secret_request": "I can't share credentials, secrets, or system details. I can help with policy questions instead.",
    "role_impersonation": "I can't act with a different role or elevated access. Your permissions come from your verified login, so I can only show what your role allows.",
    "missing_question": "Please type a question about the policies available to you.",
    "too_long": "That question is too long - please shorten it and try again.",
}

SMALLTALK = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "thanks", "thank you", "who are you", "what can you do", "help"]

# questions about personal employee data are out of scope: this portal only serves
# the policy documents, and personal records are not part of its knowledge base.
PERSONAL_DATA_RE = re.compile(
    "|".join(
        [
            r"\bmy\s+(personal\s+)?records?\b",
            r"\bpersonal\s+records?\b",
            r"\bmy\s+(leave\s+balance|remaining\s+leave|leave\s+left|salary|payslip|payroll|employee\s+id|review\s+score|access\s+level|profile|details|data)\b",
            r"\b(show|give|get|list|view)\s+(me\s+)?(all\s+)?(employee\s+)?records\b",
            r"\brecords?\s+(of|for)\s+\w+",
            r"\bemployee\s+directory\b",
        ]
    ),
    re.IGNORECASE,
)


def _guard_reason(question: str, role: str) -> str | None:
    q = question.strip()
    if not q:
        return "missing_question"
    if len(q) > 2000:
        return "too_long"
    for pattern, reason in INJECTION_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            return reason
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            return "secret_request"
    match = IMPERSONATION_RE.search(q)
    if match:
        claimed = _CLAIMED_ROLE.get(match.group(1).lower())
        if claimed and claimed != role:
            return "role_impersonation"
    return None


def guard_node(state: dict) -> dict:
    started = time.perf_counter()
    reason = _guard_reason(state["question"], state["role"])
    entry = {
        "step": len(state.get("trace") or []) + 1,
        "node": "guard",
        "status": "blocked" if reason else "passed",
        "detail": reason or f"input accepted ({len(state['question'])} chars)",
        "ms": int((time.perf_counter() - started) * 1000),
    }
    if reason:
        return {"blocked": True, "guard_reason": reason, "refusal": REFUSALS[reason], "trace": [entry]}
    return {"blocked": False, "trace": [entry]}


# --------------------------------------------------------------------- route
def route_node(state: dict) -> dict:
    started = time.perf_counter()
    question = state["question"]
    ql = question.lower()
    tokens = re.findall(r"[a-z0-9]+", ql)

    if len(tokens) <= 6 and any(ql.startswith(word) or ql == word for word in SMALLTALK):
        route = "smalltalk"
    elif PERSONAL_DATA_RE.search(question):
        route = "out_of_scope"
    else:
        route = "policy"

    entry = {"step": len(state.get("trace") or []) + 1, "node": "route", "status": "ok", "detail": route, "ms": int((time.perf_counter() - started) * 1000)}
    return {"route": route, "trace": [entry]}


# --------------------------------------------------------------------- policy search (rag retrieval)
def policy_search_node(state: dict) -> dict:
    started = time.perf_counter()
    settings = get_settings()
    results = search_policies(state["question"], state["role"], k=settings.rag_top_k)
    relevant = [
        r for r in results
        if r.get("distance") is None or r["distance"] <= settings.rag_max_distance
    ]
    doc_ids = sorted({r["doc_id"] for r in relevant})
    detail = (
        f"{len(relevant)}/{len(results)} retrieved chunk(s) within relevance cutoff "
        f"(cosine distance <= {settings.rag_max_distance})"
    )
    if doc_ids:
        detail += f" from {len(doc_ids)} accessible document(s): {', '.join(doc_ids)}"
    detail += f" (metadata filter: role_{state['role']}=true)"
    entry = {"step": len(state.get("trace") or []) + 1, "node": "policy_search", "status": "ok" if relevant else "no_match", "detail": detail, "ms": int((time.perf_counter() - started) * 1000)}

    out: dict = {"retrieved": relevant, "trace": [entry]}
    if not relevant:
        out["route"] = "out_of_scope"
    return out


# --------------------------------------------------------------------- answer
def _extractive_answer(question: str, sources: list[dict]) -> str | None:
    """Offline mode: pick the sentences with the highest keyword overlap with the question."""
    stopwords = {"the", "a", "an", "is", "are", "do", "does", "how", "what", "when", "who", "where", "why", "i", "my", "me", "we", "our", "you", "your", "and", "or", "of", "to", "in", "on", "for", "with", "about", "can", "many", "much", "m", "am", "be", "it", "this", "that", "there", "if", "at", "as", "by"}

    def keywords(text: str) -> set[str]:
        return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2 and t not in stopwords}

    qkw = keywords(question)
    scored: list[tuple[int, int, str]] = []
    for si, src in enumerate(sources):
        for sentence in re.split(r"\n+|(?<=[.!?])\s+", src["text"]):
            sentence = sentence.strip().lstrip("-*#").strip()
            if len(sentence) < 40:
                continue
            overlap = len(qkw & keywords(sentence))
            scored.append((overlap, si, sentence))
    scored.sort(key=lambda item: (-item[0], item[1]))
    if not scored or scored[0][0] == 0:
        return None

    picked: list[tuple[int, str]] = []
    seen: set[str] = set()
    for overlap, si, sentence in scored:
        if overlap == 0:
            break
        signature = sentence[:64]
        if signature in seen:
            continue
        seen.add(signature)
        picked.append((si, sentence))
        if len(picked) >= 4:
            break

    lines = [f"- {sentence} [S{si + 1}]" for si, sentence in picked]
    return "Based on the policies available to your role, here is the relevant guidance:\n\n" + "\n".join(lines)


def _smalltalk_answer(state: dict) -> str:
    if llm_active():
        reply = llm_chat(
            [
                {"role": "system", "content": prompts.SMALLTALK_SYSTEM},
                {"role": "user", "content": f"{state['question']}\n(The user is {state['full_name']}, role: {state['role']}.)"},
            ],
            max_tokens=120,
        )
        if reply:
            return reply
    first_name = (state.get("full_name") or state["username"]).split()[0]
    return (
        f"Hi {first_name}! I can answer questions based on the policy documents available to your role "
        f"({state['role']}). Ask away - for example, about leave, remote work, or information security."
    )


def _out_of_scope_answer(state: dict) -> str:
    if PERSONAL_DATA_RE.search(state["question"]):
        return prompts.PERSONAL_DATA_ANSWER
    return prompts.OUT_OF_SCOPE_ANSWER


def answer_node(state: dict) -> dict:
    started = time.perf_counter()
    route = state.get("route")
    ms = lambda: int((time.perf_counter() - started) * 1000)  # noqa: E731

    if route == "smalltalk":
        answer = _smalltalk_answer(state)
        entry = {"step": len(state.get("trace") or []) + 1, "node": "answer", "status": "ok", "detail": "smalltalk reply", "ms": ms()}
        return {"answer": answer, "trace": [entry]}

    if route == "out_of_scope":
        answer = _out_of_scope_answer(state)
        entry = {"step": len(state.get("trace") or []) + 1, "node": "answer", "status": "out_of_scope", "detail": "question outside the policy knowledge base", "ms": ms()}
        return {"answer": answer, "trace": [entry]}

    sources = state.get("retrieved") or []
    attempts = state.get("attempts", 0) + 1
    if not sources:
        entry = {"step": len(state.get("trace") or []) + 1, "node": "answer", "status": "no_sources", "detail": "no relevant chunks after the role filter and relevance cutoff", "ms": ms()}
        return {"answer": prompts.OUT_OF_SCOPE_ANSWER, "attempts": attempts, "trace": [entry]}

    mode = "extractive"
    answer = None
    if llm_active():
        system_prompt = prompts.POLICY_ANSWER_SYSTEM
        if state.get("evidence_retry"):
            system_prompt += prompts.POLICY_ANSWER_RETRY_SUFFIX
        answer = llm_chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User role: {state['role']}\n\nQuestion: {state['question']}\n\nSOURCES:\n{prompts.build_sources_block(sources)}"},
            ],
            max_tokens=650,
        )
        if answer:
            mode = "llm"
    if not answer:
        answer = _extractive_answer(state["question"], sources)
    if not answer:
        entry = {"step": len(state.get("trace") or []) + 1, "node": "answer", "status": "out_of_scope", "detail": "retrieved chunks had no overlap with the question", "ms": ms()}
        return {"answer": prompts.OUT_OF_SCOPE_ANSWER, "attempts": attempts, "trace": [entry]}

    entry = {"step": len(state.get("trace") or []) + 1, "node": "answer", "status": "ok", "detail": f"{mode}, {len(sources)} source chunk(s)", "ms": ms()}
    return {"answer": answer, "attempts": attempts, "evidence_retry": False, "trace": [entry]}


# --------------------------------------------------------------------- citation check
def _make_citation(index: int, source: dict) -> dict:
    snippet = re.sub(r"\s+", " ", source["text"]).strip()[:240]
    return {
        "label": f"S{index}",
        "doc_id": source["doc_id"],
        "title": source["title"],
        "section": source["section"],
        "snippet": snippet,
        "roles": source["roles"],
    }


def citation_check_node(state: dict) -> dict:
    started = time.perf_counter()
    route = state.get("route")
    sources = state.get("retrieved") or []
    answer = state.get("answer", "")
    ms = lambda: int((time.perf_counter() - started) * 1000)  # noqa: E731

    if route != "policy" or not sources:
        entry = {"step": len(state.get("trace") or []) + 1, "node": "citation_check", "status": "skipped", "detail": f"no citation requirement (route={route})", "ms": ms()}
        return {"citation_ok": True, "trace": [entry]}

    if prompts.OUT_OF_SCOPE_ANSWER in answer or prompts.PERSONAL_DATA_ANSWER in answer:
        entry = {"step": len(state.get("trace") or []) + 1, "node": "citation_check", "status": "skipped", "detail": "out-of-scope answer requires no citations", "ms": ms()}
        return {"citation_ok": True, "trace": [entry]}

    # 1) leak scan: the answer must never name documents the role cannot access
    restricted = [doc for doc in load_policy_index() if state["role"] not in doc["roles"]]
    answer_lower = answer.lower()
    for doc in restricted:
        if doc["title"].lower() in answer_lower or (doc["id"] and doc["id"].lower() in answer_lower):
            with SessionLocal() as db:
                log_event(db, actor=state["username"], role=state["role"], action="citation_leak_blocked", resource=doc["id"], decision="deny", detail="answer referenced a restricted document; replaced with refusal", ip=state.get("ip", ""))
            safe = "I'm not able to share details from policies that aren't available to your role. If you need this information, please ask HR or your administrator."
            entry = {"step": len(state.get("trace") or []) + 1, "node": "citation_check", "status": "blocked_leak", "detail": f"restricted reference '{doc['id']}' removed", "ms": ms()}
            return {"answer": safe, "citations": [], "citation_ok": True, "guard_reason": "restricted_content_blocked", "trace": [entry]}

    # 2) every inline [S#] label must map to a retrieved source
    labels = sorted({int(m) for m in re.findall(r"\[S(\d+)\]", answer)})
    valid = [i for i in labels if 1 <= i <= len(sources)]
    if not valid:
        attempts = state.get("attempts", 1)
        if attempts < 2:
            entry = {"step": len(state.get("trace") or []) + 1, "node": "citation_check", "status": "retry", "detail": "answer had no valid citations - asking the model again", "ms": ms()}
            return {"citation_ok": False, "evidence_retry": True, "trace": [entry]}
        entry = {"step": len(state.get("trace") or []) + 1, "node": "citation_check", "status": "unverified", "detail": "citations could not be verified; disclaimer added", "ms": ms()}
        return {"answer": answer + "\n\n_Note: source citations could not be verified for this answer._", "citation_ok": True, "trace": [entry]}

    citations = [_make_citation(i, sources[i - 1]) for i in valid]
    entry = {"step": len(state.get("trace") or []) + 1, "node": "citation_check", "status": "ok", "detail": f"{len(citations)} verified citation(s)", "ms": ms()}
    return {"citations": citations, "citation_ok": True, "trace": [entry]}
