"""Policy Bot - Streamlit front end.

Run from the project root:
    streamlit run streamlit_app.py

The app talks to the FastAPI backend on 127.0.0.1:8000 and starts it
automatically if it is not already running.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent
API_BASE = os.environ.get("POLICYBOT_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Policy Bot", page_icon=":material/policy:", layout="centered")


# --------------------------------------------------------------------- backend management
def _health(timeout: float = 1.5) -> dict | None:
    try:
        response = requests.get(f"{API_BASE}/health", timeout=timeout)
        if response.status_code == 200 and response.json().get("app") == "Policy Bot":
            return response.json()
    except requests.RequestException:
        return None
    return None


@st.cache_resource(show_spinner=False)
def ensure_backend() -> dict | None:
    """Return backend health info, starting the FastAPI server if needed."""
    health = _health()
    if health:
        return health

    log_path = ROOT / "data" / "api.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with open(log_path, "a", encoding="utf-8") as log_file:
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(ROOT),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
    for _ in range(240):
        time.sleep(1)
        health = _health()
        if health:
            return health
    return None


def api(method: str, path: str, token: str | None = None, timeout: int = 180, **kwargs):
    """Small API helper -> (json | None, error | None)."""
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(method, f"{API_BASE}{path}", headers=headers, timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        return None, f"API unreachable: {exc}"
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:  # noqa: BLE001
            detail = response.text
        if isinstance(detail, list):  # pydantic validation errors
            detail = "; ".join(str(item.get("msg", item)) for item in detail)
        return None, str(detail)
    try:
        return response.json(), None
    except Exception:  # noqa: BLE001
        return {}, None


def logout() -> None:
    for key in ("token", "user", "messages", "history_loaded"):
        st.session_state.pop(key, None)


def show_error(err: str) -> None:
    if "token" in err.lower() and ("expired" in err.lower() or "invalid" in err.lower()):
        logout()
        st.rerun()
    st.error(err)


def short_ts(ts: str) -> str:
    return ts.replace("T", " ")[:16]


# --------------------------------------------------------------------- auth page
DEMO_ACCOUNTS = (
    "| username | password | role |\n|---|---|---|\n"
    "| alice | `EmployeePass!123` | employee |\n"
    "| priya | `HrPass!123` | hr |\n"
    "| sam | `AdminPass!123` | admin |\n"
)


def login_page() -> None:
    st.title("Policy Bot")
    st.caption("Role-based policy assistant - sign in or create an account")

    sign_in, sign_up = st.tabs(["Sign in", "Sign up"])

    with sign_in:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            if not username.strip() or not password:
                st.error("Please enter both username and password.")
            else:
                data, err = api("POST", "/api/auth/login", timeout=30, json={"username": username.strip(), "password": password})
                if err:
                    st.error(err)
                else:
                    st.session_state.token = data["access_token"]
                    st.session_state.user = data["user"]
                    st.rerun()
        with st.expander("Demo accounts (optional)"):
            st.markdown(DEMO_ACCOUNTS)

    with sign_up:
        with st.form("signup_form"):
            full_name = st.text_input("Full name")
            new_username = st.text_input("Username", help="3-32 characters: letters, digits, dot, dash, underscore")
            new_password = st.text_input("Password", type="password", help="At least 8 characters")
            confirm_password = st.text_input("Confirm password", type="password")
            role = st.selectbox("Role", ["employee", "hr", "admin"], help="Role decides which policy documents and chat answers you get")
            created = st.form_submit_button("Create account", use_container_width=True)
        if created:
            problems = []
            if len(full_name.strip()) < 2:
                problems.append("Please enter your full name.")
            if len(new_username.strip()) < 3:
                problems.append("Username must be at least 3 characters.")
            if len(new_password) < 8:
                problems.append("Password must be at least 8 characters.")
            if new_password != confirm_password:
                problems.append("Passwords do not match.")
            if problems:
                for problem in problems:
                    st.error(problem)
            else:
                data, err = api(
                    "POST",
                    "/api/auth/signup",
                    timeout=30,
                    json={"full_name": full_name.strip(), "username": new_username.strip(), "password": new_password, "role": role},
                )
                if err:
                    st.error(err)
                else:
                    st.success(f"Account created for {data['full_name']} (role: {data['role']}). Use the Sign in tab with your username and password.")


# --------------------------------------------------------------------- sidebar
def sidebar(health: dict) -> str:
    user = st.session_state.user
    with st.sidebar:
        st.title("Policy Bot")
        st.markdown(f"**{user['full_name']}**")
        st.caption(f"@{user['username']} - role: {user['role']}")
        options = ["Ask the bot", "Policies & Documents", "About"]
        if user["role"] == "admin":
            options.append("Audit Log")
        page = st.radio("Menu", options, label_visibility="collapsed")
        st.divider()
        st.caption(f"{health.get('documents', '?')} policies - {health.get('chunks', '?')} indexed chunks")
        if st.button("Sign out", use_container_width=True):
            api("POST", "/api/auth/logout", token=st.session_state.token, timeout=10)
            logout()
            st.rerun()
    return page


# --------------------------------------------------------------------- chat
def ask_bot(question: str) -> None:
    st.session_state.messages.append({"kind": "user", "text": question})
    with st.spinner("Searching the policy documents..."):
        data, err = api("POST", "/api/chat/query", token=st.session_state.token, json={"question": question})
    if err:
        st.session_state.messages.append({"kind": "assistant", "text": f"Error: {err}", "error": True})
    else:
        st.session_state.messages.append(
            {
                "kind": "assistant",
                "text": data["answer"],
                "citations": data.get("citations", []),
                "blocked": data.get("blocked", False),
            }
        )
    st.rerun()


def load_history() -> None:
    if st.session_state.get("history_loaded"):
        return
    st.session_state.history_loaded = True
    data, err = api("GET", "/api/chat/history", token=st.session_state.token, timeout=30)
    if err or not data:
        st.session_state.setdefault("messages", [])
        return
    messages = []
    for item in data:
        messages.append({"kind": "user", "text": item["question"]})
        messages.append({"kind": "assistant", "text": item["answer"], "blocked": item.get("blocked", False)})
    st.session_state.messages = messages


def render_assistant(message: dict) -> None:
    with st.chat_message("assistant"):
        if message.get("error"):
            st.error(message["text"])
            return
        if message.get("blocked"):
            st.error("Blocked by the security guard.")
        st.markdown(message["text"])
        citations = message.get("citations") or []
        if citations:
            with st.expander(f"Sources ({len(citations)})"):
                for citation in citations:
                    st.markdown(
                        f"**[{citation['label']}] {citation['doc_id']} - {citation['title']}**  \n"
                        f"{citation.get('snippet', '')}"
                    )


def page_chat(user: dict) -> None:
    load_history()
    st.subheader("Ask the bot")
    if not st.session_state.get("messages"):
        st.caption(
            "The bot answers only from the policy documents available to your role - "
            "if a question is outside them, it will say so."
        )

    for message in st.session_state.get("messages", []):
        if message["kind"] == "user":
            with st.chat_message("user"):
                st.markdown(message["text"])
        else:
            render_assistant(message)

    typed = st.chat_input("Ask about the policies available to your role...")
    if typed and typed.strip():
        ask_bot(typed.strip())


# --------------------------------------------------------------------- documents
def page_documents(user: dict) -> None:
    st.subheader("Policies & Documents")
    data, err = api("GET", "/api/documents", token=st.session_state.token, timeout=30)
    if err:
        show_error(err)
        return

    accessible, restricted = data["accessible"], data["restricted"]
    st.caption(f"Your role ({user['role']}) can open {len(accessible)} of {len(accessible) + len(restricted)} documents.")

    options = [f"{doc['doc_id']} - {doc['title']}" for doc in accessible]
    choice = st.selectbox("Open a document", options)
    if choice:
        doc_id = choice.split(" - ")[0]
        detail, detail_err = api("GET", f"/api/documents/{doc_id}", token=st.session_state.token, timeout=30)
        if detail_err:
            show_error(detail_err)
        else:
            st.markdown(f"#### {detail['title']}")
            st.caption(
                f"{detail['doc_id']} - {detail['category']} - effective {detail['effective_date']} - owner: {detail['owner']}"
            )
            st.markdown(detail["content"])

    if restricted:
        st.divider()
        st.markdown("**Not available to your role**")
        for item in restricted:
            st.markdown(f"- {item['doc_id']} - {item['title']}")
        st.caption("Opening one of these returns HTTP 403 and is recorded in the audit log.")


# --------------------------------------------------------------------- audit (admin only)
def page_audit(user: dict) -> None:
    st.subheader("Audit Log")
    limit = st.slider("Entries to show", 20, 300, 50, step=20)
    rows, err = api("GET", f"/api/admin/audit?limit={limit}", token=st.session_state.token, timeout=30)
    if err:
        show_error(err)
        return
    st.dataframe(
        [
            {
                "time (UTC)": short_ts(row["ts"]),
                "actor": row["actor"],
                "action": row["action"],
                "decision": row["decision"],
                "detail": row["detail"][:60],
            }
            for row in rows
        ],
        use_container_width=True,
        hide_index=True,
        height=440,
    )


# --------------------------------------------------------------------- about (profile + history)
def page_about(user: dict) -> None:
    st.subheader("About")
    st.markdown(f"**Name:** {user['full_name']}")
    st.markdown(f"**Username:** {user['username']}")
    st.markdown(f"**Role:** {user['role']}")

    st.divider()
    st.markdown("#### Your recent questions")
    history, err = api("GET", "/api/chat/history?limit=50", token=st.session_state.token, timeout=30)
    if err:
        show_error(err)
    elif not history:
        st.caption("You haven't asked anything yet.")
    else:
        for item in reversed(history):
            flag = " _(blocked)_" if item.get("blocked") else ""
            st.markdown(f"- `{short_ts(item['ts'])}` {item['question']}{flag}")

    st.markdown("#### Documents you have viewed")
    views, views_err = api("GET", "/api/documents/history?limit=50", token=st.session_state.token, timeout=30)
    if views_err:
        show_error(views_err)
    elif not views:
        st.caption("You haven't opened any documents yet.")
    else:
        for item in views:
            st.markdown(f"- `{short_ts(item['ts'])}` {item['doc_id']} - {item['title']}")

    st.divider()
    st.caption(
        "Policy Bot answers questions through a RAG pipeline: the policy documents are chunked and embedded "
        "into a vector store, each question is embedded and matched only against the chunks your role can "
        "access, and answers are generated from those matched chunks with source citations. Questions outside "
        "the documents get an honest 'not found' reply."
    )
    st.caption("API docs: http://127.0.0.1:8000/docs")


# --------------------------------------------------------------------- main
def main() -> None:
    health = ensure_backend()
    if health is None:
        st.error(
            "The backend API did not start within 4 minutes. Check `data/api.log`, or start it manually with "
            "`uvicorn app.main:app --port 8000`."
        )
        st.stop()

    if "token" not in st.session_state:
        login_page()
        return

    try:
        page = sidebar(health)
    except Exception:  # token invalid mid-session
        logout()
        st.rerun()
        return

    user = st.session_state.user
    if page == "Ask the bot":
        page_chat(user)
    elif page == "Policies & Documents":
        page_documents(user)
    elif page == "Audit Log":
        page_audit(user)
    else:
        page_about(user)


main()
