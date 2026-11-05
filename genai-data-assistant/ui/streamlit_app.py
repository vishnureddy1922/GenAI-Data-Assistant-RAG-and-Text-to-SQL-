"""Chat UI for the GenAI Data Assistant.

streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("ASSISTANT_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Data Assistant", page_icon="📊", layout="wide")
st.title("Data Assistant")
st.caption("Ask about sales numbers or about what our metrics mean. Numbers come from SQL, definitions from the docs.")

with st.sidebar:
    st.subheader("Try asking")
    examples = [
        "What was total revenue by month in 2025?",
        "Top 5 products by revenue last quarter",
        "Which country has the most platinum customers?",
        "How is average order value defined?",
        "When is the warehouse refreshed?",
        "Can I use product list price for historical revenue?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["pending"] = ex
    route = st.radio("Route", ["auto", "sql", "docs"], horizontal=True)

if "history" not in st.session_state:
    st.session_state["history"] = []


def render(resp: dict) -> None:
    st.markdown(resp["answer"])
    if resp.get("error"):
        st.warning(resp["error"])
    if resp["route"] == "sql" and resp.get("sql"):
        with st.expander("SQL"):
            st.code(resp["sql"], language="sql")
        if resp.get("rows"):
            df = pd.DataFrame(resp["rows"], columns=resp["columns"])
            st.dataframe(df, use_container_width=True, hide_index=True)
            numeric = df.select_dtypes("number").columns
            if len(df) > 1 and len(numeric) >= 1 and len(df.columns) >= 2:
                st.bar_chart(df.set_index(df.columns[0])[numeric[0]])
    if resp.get("sources"):
        with st.expander("Sources"):
            for s in resp["sources"]:
                st.markdown(f"[{s['ref']}] `{s['source']}` - {s['section']}")
    st.caption(f"route: {resp['route']} · {resp.get('latency_ms', 0)} ms")


for turn in st.session_state["history"]:
    with st.chat_message("user"):
        st.markdown(turn["question"])
    with st.chat_message("assistant"):
        render(turn)

question = st.chat_input("Ask a question about the data") or st.session_state.pop("pending", None)
if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                payload = {"question": question, "route": None if route == "auto" else route}
                r = requests.post(f"{API_URL}/ask", json=payload, timeout=120)
                r.raise_for_status()
                resp = r.json()
            except requests.RequestException as exc:
                st.error(f"API error: {exc}")
                st.stop()
        render(resp)
    st.session_state["history"].append(resp)
