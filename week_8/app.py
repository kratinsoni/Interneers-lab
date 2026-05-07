import os
import re
import streamlit as st
from pathlib import Path
from openai import OpenAI
from rag import retrieve_relevant_chunks, load_vector_store, ingest_all

st.set_page_config(page_title="RAG DEMO", page_icon="🤖", layout="wide")

st.markdown(
    """
<style>
/* Main container */
.block-container { max-width: 860px; padding-top: 2rem; }
 
/* Chat bubbles */
.chat-user {
    background: #4F46E5;
    color: white;
    padding: 12px 16px;
    border-radius: 18px 18px 4px 18px;
    margin: 6px 0;
    max-width: 80%;
    margin-left: auto;
    font-size: 0.95rem;
}
.chat-assistant {
    background: #F1F5F9;
    color: #1E293B;
    padding: 12px 16px;
    border-radius: 18px 18px 18px 4px;
    margin: 6px 0;
    max-width: 80%;
    font-size: 0.95rem;
    border: 1px solid #E2E8F0;
}
.source-badge {
    display: inline-block;
    background: #EEF2FF;
    color: #4338CA;
    border: 1px solid #C7D2FE;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.75rem;
    margin: 2px 3px;
    font-family: monospace;
}
.score-small { color: #94A3B8; font-size: 0.72rem; }
.section-header {
    font-size: 0.78rem;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
}
</style>
""",
    unsafe_allow_html=True,
)


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    try:
        OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        OPENAI_API_KEY = ""


if "messages" not in st.session_state:
    st.session_state.messages = []
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "db_ready" not in st.session_state:
    st.session_state.db_ready = False


with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/869/869636.png", width=60)
    st.title("⚙️ Settings")
    st.divider()

    api_key_input = st.text_input(
        "OpenAI API Key",
        value=OPENAI_API_KEY,
        type="password",
        placeholder="sk-...",
        help="Required for embeddings and chat completions.",
    )    

    if api_key_input:
        OPENAI_API_KEY = api_key_input
        os.environ["OPENAI_API_KEY"] = api_key_input

    st.divider()

    top_k = st.slider("Chunks to retrieve (k)", min_value=1, max_value=10, value=3, step=1)

    show_sources = st.checkbox("Show Source Documents", value=True)

    st.divider()

    if st.button("🗄️ (Re-)Ingest Documents", use_container_width=True):
        if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
            st.error("Please enter a valid OpenAI API key first.")
        else:
            with st.spinner("Ingesting documents and building vector store..."):
                try:
                    st.session_state.vectorstore = ingest_all()
                    st.session_state.db_ready = True
                    st.success("✅ Ingestion complete! You can now ask questions.")
                except Exception:
                    pass

    status_color = "🟢" if st.session_state.db_ready else "🔴"
    st.caption(
        f"{status_color} Vector DB: {'Ready' if st.session_state.db_ready else 'Not loaded'}"
    )

    st.divider()

    if st.button("❌ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.success("Chat history cleared.")
        st.rerun()

    st.caption("Made with ❤️ by Interneers Lab")

col1, col2 = st.columns([1, 8])

with col1:
    st.markdown("## 🤖")
with col2:
    st.markdown("## Ask the Expert")
    st.caption(
        "Your AI-powered assistant for BuildRight product manuals, return policies, and vendor guidelines."
    )

st.divider()

chat_container = st.container()

with chat_container:
    if not st.session_state.messages:
        st.markdown(
            """
        <div style="text-align:center; color:#94A3B8; margin-top:40px;">
            <div style="font-size:2.5rem">💬</div>
            <div style="font-size:1rem; margin-top:8px;">Ask me anything about BuildRight products, returns, or vendor policies.</div>
            <div style="font-size:0.85rem; margin-top:6px; color:#CBD5E1;">
            Try: <i>"What is the warranty period for the Lego Castle?"</i> or
            <i>"What's the return policy for damaged items?"</i>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="chat-assistant">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
            # Show sources if stored
            if show_sources and "chunks" in msg:
                with st.expander("📄 Retrieved context chunks", expanded=False):
                    for i, c in enumerate(msg["chunks"], 1):
                        source_label = c["source"].replace("_", " ").title()
                        st.markdown(
                            f'<span class="source-badge">📁 {source_label}</span>'
                            f'<span class="score-small"> score: {c["score"]}</span>',
                            unsafe_allow_html=True,
                        )
                        st.code(c["content"], language=None)
                        if i < len(msg["chunks"]):
                            st.divider()

# Suggested Questions
if not st.session_state.messages:
    st.markdown(
        '<div class="section-header">Suggested questions</div>', unsafe_allow_html=True
    )
    suggestions = [
        "What is the warranty period for the Lego Castle?",
        "What's the return policy for damaged items?",
        "What are the payment terms for vendors?",
        "How do I return a defective RC Racing Car?",
        "What safety certifications do toy vendors need?",
    ]
    cols = st.columns(len(suggestions))
    for col, sug in zip(cols, suggestions):
        with col:
            if st.button(sug, key=f"sug_{sug[:20]}", use_container_width=True):
                st.session_state._pending_query = sug
                st.rerun()

pending = st.session_state.pop("_pending_query", None)

user_input = st.chat_input("Type your question here...", key="user_input")

query = pending or user_input

def get_answer(query: str, vector_store, api_key: str, top_k: int = 3) -> tuple[str, list[dict]]:
    chunks = retrieve_relevant_chunks(query, vector_store=vector_store, top_k=top_k)

    context = "\n\n---\n\n".join(
        f"[Source: {c['source'].replace('_', ' ').title()}]\n{c['content']}"
        for c in chunks
    )

    system_prompt = """You are an expert assistant for BuildRight Toys. 
        Answer the user's question ONLY using the context provided below.
        Be helpful, concise, and accurate. If the context doesn't contain enough 
        information to answer fully, say so honestly.
        Cite the source document name when referencing specific policies or details."""
    
    client = OpenAI(api_key=api_key)

    reponse = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ],
        temperature=0.2,
        max_tokens=600,
    )

    answer = reponse.choices[0].message.content.strip()

    return answer, chunks

# process query
if query:
    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
        st.warning("⚠️ Please enter your OpenAI API key in the sidebar.")
    elif not st.session_state.db_ready:
        st.warning("⚠️ Knowledge base not loaded. Click '(Re-)Ingest Documents' in the sidebar.")
    else:
        st.session_state.messages.append({"role": "user", "content": query})

        with st.spinner("Searching knowledge base.."):
            try:
                answer, chunks = get_answer(query, st.session_state.vectorstore, OPENAI_API_KEY, top_k)
                st.session_state.messages.append({"role": "assistant", "content": answer, "chunks": chunks})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": "Sorry, something went wrong while fetching the answer.", "chunks": []})
        
        st.rerun()
