import glob, json, os, time
import streamlit as st
from pipeline import handle_transcript, ask
from qdrant_store import qdrant, COLLECTION, ensure_collection

st.set_page_config(page_title="Meeting-to-Action Agent", layout="wide")
st.title("Meeting-to-Action Agent")
st.caption("Omi (voice) → Lyzr (agents) → Qdrant (memory) → Autonomous actions")

# Sidebar: send a transcript manually (Omi simulation)
st.sidebar.header("Send a transcript")
sample = open("sample_transcript.txt").read() if os.path.exists("sample_transcript.txt") else ""
text = st.sidebar.text_area("Transcript", sample, height=220)
if st.sidebar.button("Process transcript"):
    with st.spinner("Agents working..."):
        items = handle_transcript(text)
    st.sidebar.success(f"Extracted {len(items)} tasks")
auto = st.sidebar.checkbox("Auto-refresh every 5s")

tab_log, tab_mem, tab_act, tab_ask = st.tabs(
    ["Agent log", "Memory (Qdrant)", "Actions taken", "Ask your meetings"])

with tab_log:
    st.subheader("What each agent did")
    rows = []
    if os.path.exists("outputs/agent_log.jsonl"):
        rows = [json.loads(l) for l in open("outputs/agent_log.jsonl") if l.strip()]
    st.dataframe(list(reversed(rows[-100:])), use_container_width=True)

with tab_mem:
    st.subheader("Stored memory")
    ensure_collection()
    points, _ = qdrant.scroll(COLLECTION, limit=200, with_payload=True)
    cols = ["task", "owner", "person", "deadline", "type", "priority"]
    st.dataframe([{c: p.payload.get(c) for c in cols} for p in points],
                 use_container_width=True)

with tab_act:
    st.subheader("Autonomous actions")
    drafts = sorted(glob.glob("outputs/email_draft_*.txt"))
    if not drafts:
        st.info("No actions yet.")
    for path in drafts:
        with st.expander(os.path.basename(path)):
            st.code(open(path).read())

with tab_ask:
    q = st.text_input("Ask about past meetings", "What did I promise Rahul?")
    if st.button("Ask"):
        with st.spinner("Searching memory..."):
            st.write(ask(q))

if auto:
    time.sleep(5)
    st.rerun()