import json
from datetime import datetime
import os
import uuid
from dotenv import load_dotenv
import streamlit as st

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Databases
# ─────────────────────────────────────────────────────────────────────────────

PRODUCT_DB = {
    "LEGO-001": {
        "product_id": "LEGO-001",
        "name": "Classic Building Blocks Set",
        "brand": "Lego",
        "category": "Educational Toys",
        "unit_price": 4.99,
        "currency": "USD",
        "description": "Standard colourful building blocks.",
        "min_order_qty": 10,
        "emoji": "🧱",
    },
    "LEGO-002": {
        "product_id": "LEGO-002",
        "name": "Technic Gear Pack",
        "brand": "Lego",
        "category": "STEM Toys",
        "unit_price": 8.49,
        "currency": "USD",
        "description": "Gears, axles, connectors for Technic builds.",
        "min_order_qty": 5,
        "emoji": "⚙️",
    },
    "LEGO-003": {
        "product_id": "LEGO-003",
        "name": "Duplo Starter Kit",
        "brand": "Lego",
        "category": "Preschool Toys",
        "unit_price": 3.25,
        "currency": "USD",
        "description": "Large toddler-safe bricks.",
        "min_order_qty": 20,
        "emoji": "🔴",
    },
}

INVENTORY_DB = {
    "LEGO-001": {"stock": 250, "reserved": 40,  "restock_date": "2026-05-20", "warehouse": "Mumbai-WH1"},
    "LEGO-002": {"stock": 80,  "reserved": 10,  "restock_date": "2026-05-15", "warehouse": "Mumbai-WH1"},
    "LEGO-003": {"stock": 15,  "reserved": 5,   "restock_date": "2026-05-25", "warehouse": "Mumbai-WH2"},
}

DISCOUNT_RULES = [
    {"min_qty": 100, "discount_pct": 20, "label": "Bulk (100+)"},
    {"min_qty": 50,  "discount_pct": 10, "label": "Volume (50-99)"},
    {"min_qty": 20,  "discount_pct": 5,  "label": "Standard (20-49)"},
    {"min_qty": 0,   "discount_pct": 0,  "label": "No discount (<20)"},
]

# ─────────────────────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_product_info(product_id: str) -> dict:
    """Retrieve full product details for a given product ID. Available IDs: LEGO-001, LEGO-002, LEGO-003."""
    product = PRODUCT_DB.get(product_id.upper())
    if not product:
        return {"error": f"Product '{product_id}' not found.", "available_ids": list(PRODUCT_DB.keys())}
    return {"status": "ok", "product": product}


@tool
def check_inventory(product_id: str) -> dict:
    """Check current Week 3 stock levels for a product."""
    inv = INVENTORY_DB.get(product_id.upper())
    if not inv:
        return {"error": f"No inventory record for '{product_id}'."}
    available = inv["stock"] - inv["reserved"]
    return {
        "status": "ok", "product_id": product_id.upper(),
        "total_stock": inv["stock"], "reserved": inv["reserved"],
        "available": available, "restock_date": inv["restock_date"],
        "warehouse": inv["warehouse"], "week": "Week 3", "in_stock": available > 0,
    }


@tool
def calculate_quote(product_id: str, quantity: int) -> dict:
    """Calculate a price quote with tiered discounts + 18% GST."""
    product = PRODUCT_DB.get(product_id.upper())
    if not product:
        return {"error": f"Product '{product_id}' not found."}
    if quantity <= 0:
        return {"error": "Quantity must be greater than 0."}
    if quantity < product["min_order_qty"]:
        return {"error": f"Minimum order qty is {product['min_order_qty']} units."}
    rule = next(r for r in DISCOUNT_RULES if quantity >= r["min_qty"])
    unit_price = product["unit_price"]
    subtotal = unit_price * quantity
    discount_amt = subtotal * (rule["discount_pct"] / 100)
    discounted = subtotal - discount_amt
    tax_amt = discounted * 0.18
    grand_total = discounted + tax_amt
    return {
        "status": "ok", "product_id": product_id.upper(),
        "product_name": product["name"], "quantity": quantity,
        "unit_price_usd": round(unit_price, 2), "subtotal_usd": round(subtotal, 2),
        "discount_tier": rule["label"], "discount_pct": rule["discount_pct"],
        "discount_amount_usd": round(discount_amt, 2),
        "discounted_subtotal_usd": round(discounted, 2),
        "tax_rate_pct": 18, "tax_amount_usd": round(tax_amt, 2),
        "grand_total_usd": round(grand_total, 2), "currency": "USD",
        "quote_date": datetime.today().strftime("%Y-%m-%d"),
    }


TOOLS = [get_product_info, check_inventory, calculate_quote]

SYSTEM_PROMPT = """You are a helpful sales assistant for an educational toy company.

You have three tools:
  • get_product_info  — look up product details by ID
  • check_inventory   — check Week 3 stock levels
  • calculate_quote   — compute price with tiered discounts + 18% GST

Product IDs:
  LEGO-001 = Classic Building Blocks Set  ($4.99/unit)
  LEGO-002 = Technic Gear Pack            ($8.49/unit)
  LEGO-003 = Duplo Starter Kit            ($3.25/unit)

For every customer request:
1. Identify the best matching product ID.
2. Call get_product_info to confirm details.
3. Call check_inventory to verify Week 3 availability.
4. Call calculate_quote to compute the price with discounts.
5. Reply with a friendly summary AND embed a JSON invoice containing:
   invoice_number, date, customer_request,
   product (id, name, brand),
   inventory (week, available_stock, warehouse),
   pricing (unit_price, quantity, subtotal, discount_pct, discount_amount,
            tax_rate, tax_amount, grand_total, currency),
   friendly_note.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Agent (cached)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def build_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    memory = InMemorySaver()
    return create_agent(llm, TOOLS, system_prompt=SYSTEM_PROMPT, checkpointer=memory)


def run_agent(user_request: str, thread_id: str, log_callback=None):
    agent = build_agent()
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke({"messages": [HumanMessage(content=user_request)]}, config=config)

    if log_callback:
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    fn_map = {
                        "get_product_info": get_product_info,
                        "check_inventory": check_inventory,
                        "calculate_quote": calculate_quote,
                    }
                    fn = fn_map.get(tc["name"])
                    output = fn.invoke(tc["args"]) if fn else {}
                    log_callback(tc["name"], tc["args"], output)

    final = result["messages"][-1].content
    try:
        clean = final.replace("```json", "").replace("```", "")
        start = clean.index("{")
        end = clean.rindex("}") + 1
        invoice = json.loads(clean[start:end])
    except (ValueError, json.JSONDecodeError):
        invoice = {"raw_response": final}
    return invoice


# ─────────────────────────────────────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────────────────────────────────────

def new_chat_entry(name=None):
    tid = str(uuid.uuid4())
    return {
        "thread_id": tid,
        "name": name or f"Chat {datetime.now().strftime('%b %d, %H:%M')}",
        "created_at": datetime.now().isoformat(),
        "messages": [],   # list of {role, content, invoice, tool_logs}
    }

if "chats" not in st.session_state:
    st.session_state.chats = [new_chat_entry("New Chat")]
if "active_idx" not in st.session_state:
    st.session_state.active_idx = 0

def active_chat():
    return st.session_state.chats[st.session_state.active_idx]

# ─────────────────────────────────────────────────────────────────────────────
# Page config & global styles
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="LEGO Quote Agent", page_icon="🧱", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Clash+Display:wght@500;600;700&family=Cabinet+Grotesk:wght@400;500;700;800&display=swap');

/* ── Reset & base ───────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Cabinet Grotesk', 'DM Sans', sans-serif;
    background: #0a0a0f !important;
    color: #e8e8f0 !important;
}
.stApp { background: #0a0a0f !important; }

/* ── Sidebar ────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0e0e18 !important;
    border-right: 1px solid #1e1e2e !important;
    min-width: 260px !important;
}
[data-testid="stSidebar"] * { color: #c8c8e8 !important; }
[data-testid="stSidebar"] .stButton>button {
    background: transparent !important;
    border: 1px solid #2a2a3e !important;
    color: #c8c8e8 !important;
    border-radius: 10px !important;
    transition: all .2s !important;
    text-align: left !important;
    font-size: .85rem !important;
    padding: 8px 12px !important;
}
[data-testid="stSidebar"] .stButton>button:hover {
    background: #1a1a2e !important;
    border-color: #f59e0b !important;
    color: #f8fafc !important;
}

/* ── Hide default Streamlit chrome ─────────── */
header[data-testid="stHeader"] { display: none !important; }
.stDeployButton { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }

/* ── Main area ──────────────────────────────── */
.main .block-container { padding: 2rem 2.5rem 2rem !important; max-width: 1400px !important; }

/* ── Inputs ─────────────────────────────────── */
.stTextArea textarea, .stSelectbox select, div[data-baseweb="select"] {
    background: #12121e !important;
    border: 1px solid #2a2a3e !important;
    color: #e8e8f0 !important;
    border-radius: 10px !important;
    font-family: 'Cabinet Grotesk', sans-serif !important;
}
.stTextArea textarea:focus {
    border-color: #f59e0b !important;
    box-shadow: 0 0 0 2px rgba(245,158,11,.15) !important;
}

/* ── Primary button ─────────────────────────── */
.stButton>button[kind="primary"] {
    background: linear-gradient(135deg, #f59e0b, #d97706) !important;
    color: #0a0a0f !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Cabinet Grotesk', sans-serif !important;
    font-size: .95rem !important;
    transition: all .2s !important;
    letter-spacing: .3px !important;
}
.stButton>button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 20px rgba(245,158,11,.35) !important;
}

/* ── Chat bubbles ───────────────────────────── */
.msg-user {
    display: flex; justify-content: flex-end; margin: 12px 0;
}
.msg-user .bubble {
    background: linear-gradient(135deg, #1e2a3a, #162032);
    border: 1px solid #2a3a50;
    color: #c8ddf0;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    max-width: 70%;
    font-size: .92rem;
    line-height: 1.55;
}
.msg-agent {
    display: flex; justify-content: flex-start; margin: 12px 0;
    gap: 10px; align-items: flex-start;
}
.agent-avatar {
    width: 32px; height: 32px; border-radius: 50%;
    background: linear-gradient(135deg, #f59e0b, #d97706);
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0; margin-top: 2px;
}
.msg-agent .bubble {
    background: #12121e;
    border: 1px solid #1e1e2e;
    color: #c8c8e0;
    border-radius: 4px 18px 18px 18px;
    padding: 14px 18px;
    max-width: 85%;
    font-size: .92rem;
    line-height: 1.6;
}

/* ── Invoice card ───────────────────────────── */
.inv-card {
    background: linear-gradient(160deg, #12121e 0%, #0e1420 100%);
    border: 1px solid #1e2535;
    border-radius: 16px;
    padding: 26px 30px;
    margin-top: 14px;
    box-shadow: 0 20px 60px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.05);
    position: relative; overflow: hidden;
}
.inv-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #f59e0b, transparent);
}
.inv-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.inv-title { font-family: 'Clash Display', sans-serif; font-size: 1.2rem; font-weight: 700; color: #f59e0b; letter-spacing: .5px; }
.inv-num { font-size: .75rem; color: #4a4a6a; margin-top: 3px; }
.inv-product-badge {
    background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.2);
    border-radius: 8px; padding: 6px 12px; text-align: right;
}
.inv-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: .88rem; }
.inv-label { color: #5a5a7a; }
.inv-val { color: #d0d0e8; font-weight: 500; }
.inv-divider { border: none; border-top: 1px solid #1a1a2e; margin: 10px 0; }
.inv-total { font-family: 'Clash Display', sans-serif; font-size: 1.5rem; font-weight: 700; color: #34d399; }
.inv-note {
    margin-top: 16px; padding: 10px 14px;
    background: rgba(245,158,11,.07); border-left: 3px solid #f59e0b;
    border-radius: 6px; font-size: .84rem; color: #d4a85a; line-height: 1.5;
}
.stock-badge {
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    background: rgba(52,211,153,.12); border: 1px solid rgba(52,211,153,.25);
    color: #34d399; font-size: .8rem; font-weight: 600;
}
.disc-chip {
    display: inline-block; padding: 2px 8px; border-radius: 6px;
    background: rgba(52,211,153,.12); color: #34d399; font-size: .8rem; font-weight: 700;
}

/* ── Tool log ────────────────────────────────── */
.tool-log-wrap {
    background: #0d0d18; border: 1px solid #1a1a2e;
    border-radius: 10px; overflow: hidden; margin-bottom: 8px;
}
.tool-log-header {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 14px; background: #111120; border-bottom: 1px solid #1a1a2a;
    font-size: .82rem; font-weight: 600; color: #8888b0; cursor: pointer;
}
.tool-log-body { padding: 8px 14px; font-size: .79rem; color: #6666a0; line-height: 1.5; }
.tool-name { color: #f59e0b; font-weight: 700; }
.tool-badge {
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    background: rgba(245,158,11,.12); border: 1px solid rgba(245,158,11,.2);
    font-size: .72rem; color: #d4944a; font-weight: 600;
}

/* ── Chat list in sidebar ───────────────────── */
.chat-item-active {
    background: #1a1a2e !important;
    border: 1px solid #f59e0b !important;
    border-radius: 10px !important;
    color: #f8fafc !important;
}
.sidebar-logo {
    font-family: 'Clash Display', sans-serif;
    font-size: 1.3rem; font-weight: 700; color: #f59e0b;
    padding: 4px 0 16px; border-bottom: 1px solid #1e1e2e;
    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
}
.section-label {
    font-size: .7rem; font-weight: 700; letter-spacing: 1.5px;
    color: #3a3a5a; text-transform: uppercase; margin: 16px 0 8px;
}
.empty-chat {
    text-align: center; padding: 60px 20px;
    color: #3a3a5a; font-size: .95rem;
}
.empty-chat .icon { font-size: 3rem; margin-bottom: 12px; }
.page-title {
    font-family: 'Clash Display', sans-serif;
    font-size: 1.8rem; font-weight: 700; color: #e8e8f0;
    letter-spacing: -.5px; margin-bottom: 4px;
    display: flex; align-items: center; gap: 12px;
}
.thread-pill {
    font-size: .7rem; background: #1a1a2e; border: 1px solid #2a2a3e;
    color: #5a5a8a; padding: 4px 10px; border-radius: 999px; font-family: monospace;
    vertical-align: middle;
}
.stDivider { border-color: #1e1e2e !important; }
.stExpander {
    border: 1px solid #1a1a2e !important;
    border-radius: 10px !important;
    background: #0d0d18 !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — Chat History
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="sidebar-logo">🧱 QuoteAgent</div>', unsafe_allow_html=True)

    # New chat button
    if st.button("＋  New Chat", use_container_width=True, key="new_chat_btn"):
        st.session_state.chats.append(new_chat_entry())
        st.session_state.active_idx = len(st.session_state.chats) - 1
        st.rerun()

    st.markdown('<div class="section-label">Conversations</div>', unsafe_allow_html=True)

    # List all chats
    for i, chat in enumerate(st.session_state.chats):
        is_active = i == st.session_state.active_idx
        n_msgs = len(chat["messages"])
        label = f"{'💬' if is_active else '○'}  {chat['name']}"
        if n_msgs > 0:
            label += f"  ({n_msgs // 2} quote{'s' if n_msgs // 2 != 1 else ''})"

        btn_key = f"chat_btn_{i}_{chat['thread_id'][:8]}"
        clicked = st.button(label, key=btn_key, use_container_width=True)
        if clicked and not is_active:
            st.session_state.active_idx = i
            st.rerun()

    # Delete / rename
    if len(st.session_state.chats) > 0:
        st.markdown('<div class="section-label">Current Chat</div>', unsafe_allow_html=True)
        chat_ref = active_chat()
        new_name = st.text_input("Rename", value=chat_ref["name"], key="rename_input", label_visibility="collapsed")
        if new_name != chat_ref["name"]:
            st.session_state.chats[st.session_state.active_idx]["name"] = new_name
            st.rerun()

        if st.button("🗑  Delete this chat", use_container_width=True, key="delete_btn"):
            st.session_state.chats.pop(st.session_state.active_idx)
            if not st.session_state.chats:
                st.session_state.chats = [new_chat_entry("New Chat")]
            st.session_state.active_idx = max(0, st.session_state.active_idx - 1)
            st.rerun()

    st.divider()

    # Product catalog
    st.markdown('<div class="section-label">Product Catalog</div>', unsafe_allow_html=True)
    for pid, p in PRODUCT_DB.items():
        inv = INVENTORY_DB[pid]
        avail = inv["stock"] - inv["reserved"]
        st.markdown(f"**{p['emoji']} {p['name']}**  \n`{pid}` · ${p['unit_price']:.2f}/unit  \nStock: **{avail}** avail.")
        st.divider()

    st.markdown('<div class="section-label">Discount Tiers</div>', unsafe_allow_html=True)
    for rule in DISCOUNT_RULES:
        if rule["discount_pct"] > 0:
            st.markdown(f"- **{rule['discount_pct']}% off** — {rule['label']}")
    st.markdown("- No discount < 20 units")
    st.caption("+ 18% GST applies to all orders")


# ─────────────────────────────────────────────────────────────────────────────
# Main Area
# ─────────────────────────────────────────────────────────────────────────────

if not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️  `OPENAI_API_KEY` not found. Set it in your environment and restart.")
    st.stop()

chat = active_chat()

# Page header
st.markdown(
    f'<div class="page-title">💬 {chat["name"]}'
    f'<span class="thread-pill">{chat["thread_id"][:12]}…</span></div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div style="font-size:.8rem;color:#3a3a5a;margin-bottom:1.5rem;">'
    f'Thread ID: <code style="color:#4a4a6a">{chat["thread_id"]}</code>'
    f'  ·  {len(chat["messages"]) // 2} quote(s) in this session</div>',
    unsafe_allow_html=True,
)

col_chat, col_tools = st.columns([1.3, 0.9], gap="large")

with col_chat:
    # ── Conversation display ──────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        if not chat["messages"]:
            st.markdown("""
<div class="empty-chat">
  <div class="icon">🧱</div>
  <div>Start by typing a product request below</div>
  <div style="font-size:.8rem;margin-top:8px;color:#2a2a4a">
    Try: <em>"I need 60 building blocks for a school project"</em>
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            for msg in chat["messages"]:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="msg-user"><div class="bubble">{msg["content"]}</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    # Agent message
                    st.markdown(
                        '<div class="msg-agent">'
                        '<div class="agent-avatar">🧱</div>'
                        f'<div class="bubble">{msg.get("summary", "Here is your quote:")}</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                    inv = msg.get("invoice")
                    if inv and "raw_response" not in inv:
                        pricing = inv.get("pricing", inv)
                        product = inv.get("product", {})
                        inv_inf = inv.get("inventory", {})
                        pname   = product.get("name")   or inv.get("product_name", "—")
                        pid_val = product.get("id")     or inv.get("product_id", "—")
                        avail   = inv_inf.get("available_stock") or "—"
                        wh      = inv_inf.get("warehouse") or "—"
                        qty     = pricing.get("quantity", "—")
                        unit_p  = pricing.get("unit_price", "—")
                        sub     = pricing.get("subtotal", "—")
                        disc_p  = pricing.get("discount_pct", 0)
                        disc_a  = pricing.get("discount_amount", "—")
                        tax_a   = pricing.get("tax_amount", "—")
                        total   = pricing.get("grand_total", "—")
                        note    = inv.get("friendly_note", "")
                        inv_num = inv.get("invoice_number", f"INV-{datetime.today().strftime('%Y%m%d')}")

                        st.markdown(f"""
<div class="inv-card">
  <div class="inv-header">
    <div>
      <div class="inv-title">QUOTE INVOICE</div>
      <div class="inv-num">{inv_num} &nbsp;·&nbsp; {datetime.today().strftime('%d %b %Y')}</div>
    </div>
    <div class="inv-product-badge">
      <div style="font-size:.78rem;color:#5a5a7a;">Product</div>
      <div style="font-weight:600;color:#d0d0e8;font-size:.9rem">{pname}</div>
      <div style="font-size:.75rem;color:#4a4a6a">{pid_val} · {wh}</div>
    </div>
  </div>
  <div class="inv-row"><span class="inv-label">Quantity</span><span class="inv-val">{qty} units</span></div>
  <div class="inv-row"><span class="inv-label">Unit Price</span><span class="inv-val">${unit_p}</span></div>
  <div class="inv-row"><span class="inv-label">Subtotal</span><span class="inv-val">${sub}</span></div>
  <hr class="inv-divider">
  <div class="inv-row">
    <span class="inv-label">Discount <span class="disc-chip">{disc_p}% off</span></span>
    <span class="inv-val" style="color:#34d399">− ${disc_a}</span>
  </div>
  <div class="inv-row"><span class="inv-label">GST (18%)</span><span class="inv-val">${tax_a}</span></div>
  <hr class="inv-divider">
  <div class="inv-row">
    <span style="font-size:1rem;font-weight:700;color:#e8e8f0;">GRAND TOTAL</span>
    <span class="inv-total">${total}</span>
  </div>
  <div class="inv-row">
    <span class="inv-label">📦 Week 3 Stock</span>
    <span class="stock-badge">{avail} units</span>
  </div>
  {f'<div class="inv-note">💬 {note}</div>' if note else ''}
</div>
""", unsafe_allow_html=True)

                    if msg.get("invoice"):
                        with st.expander("View Raw JSON", expanded=False):
                            st.json(msg["invoice"])

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Input area ────────────────────────────────────────────────────────
    examples = [
        "— select a quick example —",
        "I need 60 building blocks for a school project, can I get a deal?",
        "We want to order 120 Duplo starter kits for a chain of preschools.",
        "How much for 30 Technic Gear Packs for a robotics club?",
        "What's the price for 15 Technic Gear Packs?",
    ]
    input_key = f"input_{chat['thread_id']}"
    prev_example_key = f"prev_example_{chat['thread_id']}"

    selected = st.selectbox("Quick examples", examples, key=f"examples_{chat['thread_id']}")

    # Only overwrite the text area when the user picks a NEW example
    if selected != examples[0] and selected != st.session_state.get(prev_example_key):
        st.session_state[input_key] = selected

    # Always track the last seen selection
    st.session_state[prev_example_key] = selected

    user_input = st.text_area(
        "Your request",
        height=90,
        placeholder="e.g. I need 60 building blocks for a school project…",
        key=input_key,
        label_visibility="collapsed",
    )
    run_btn = st.button("🚀 Get Quote", type="primary", use_container_width=True, key=f"run_{chat['thread_id']}")


with col_tools:
    st.markdown(
        '<div style="font-size:.8rem;font-weight:700;letter-spacing:1.5px;'
        'color:#3a3a5a;text-transform:uppercase;margin-bottom:12px;">Agent Tool Calls</div>',
        unsafe_allow_html=True,
    )
    tools_placeholder = st.empty()

    # Show past tool logs for messages
    existing_logs_html = ""
    for msg in chat["messages"]:
        if msg["role"] == "assistant" and msg.get("tool_logs"):
            for log in msg["tool_logs"]:
                icon = {"get_product_info": "📋", "check_inventory": "📊", "calculate_quote": "💵"}.get(log["name"], "🔧")
                snippet = json.dumps(log["result"])[:120]
                existing_logs_html += f"""
<div class="tool-log-wrap">
  <div class="tool-log-header">
    {icon} <span class="tool-name">{log['name']}</span>
    <span class="tool-badge">✓ done</span>
  </div>
  <div class="tool-log-body">
    <span style="color:#3a3a5a">Input:</span> <code style="color:#5a5a8a">{json.dumps(log['args'])}</code><br>
    <span style="color:#3a3a5a">→</span> {snippet}{'…' if len(json.dumps(log['result']))>120 else ''}
  </div>
</div>"""
    if existing_logs_html:
        tools_placeholder.markdown(existing_logs_html, unsafe_allow_html=True)
    else:
        tools_placeholder.markdown(
            '<div style="color:#2a2a4a;font-size:.85rem;padding:20px 0;">Tool calls will appear here when the agent runs…</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Handle submission
# ─────────────────────────────────────────────────────────────────────────────

if run_btn and user_input.strip():
    # Append user message immediately
    st.session_state.chats[st.session_state.active_idx]["messages"].append({
        "role": "user",
        "content": user_input.strip(),
    })

    # Auto-name chat from first message
    if len(st.session_state.chats[st.session_state.active_idx]["messages"]) == 1:
        short = user_input.strip()[:30]
        st.session_state.chats[st.session_state.active_idx]["name"] = short + ("…" if len(user_input.strip()) > 30 else "")

    live_logs = []
    live_html = ""

    def log_tool(name, args, result):
        icon = {"get_product_info": "📋", "check_inventory": "📊", "calculate_quote": "💵"}.get(name, "🔧")
        live_logs.append({"name": name, "args": args, "result": result})
        global live_html
        snippet = json.dumps(result)[:120]
        live_html += f"""
<div class="tool-log-wrap">
  <div class="tool-log-header">
    {icon} <span class="tool-name">{name}</span>
    <span class="tool-badge">running…</span>
  </div>
  <div class="tool-log-body">
    <span style="color:#3a3a5a">Input:</span> <code style="color:#5a5a8a">{json.dumps(args)}</code><br>
    <span style="color:#3a3a5a">→</span> {snippet}{'…' if len(json.dumps(result))>120 else ''}
  </div>
</div>"""
        tools_placeholder.markdown(live_html, unsafe_allow_html=True)

    with st.spinner("Agent is thinking…"):
        try:
            invoice = run_agent(
                user_input.strip(),
                thread_id=chat["thread_id"],
                log_callback=log_tool,
            )
        except Exception as e:
            st.error(f"Agent error: {e}")
            st.stop()

    # Build summary from invoice
    if "raw_response" in invoice:
        summary = invoice["raw_response"][:200]
    else:
        pricing = invoice.get("pricing", invoice)
        pname = invoice.get("product", {}).get("name") or invoice.get("product_name", "product")
        total = pricing.get("grand_total", "—")
        disc  = pricing.get("discount_pct", 0)
        summary = f"Here's your quote for **{pname}** — Grand total: **${total} USD**" + (f" ({disc}% discount applied)" if disc else "") + "."

    # Append assistant message with invoice and logs
    st.session_state.chats[st.session_state.active_idx]["messages"].append({
        "role": "assistant",
        "summary": summary,
        "invoice": invoice,
        "tool_logs": live_logs,
    })

    st.rerun()

elif run_btn:
    st.warning("Please enter a request first.")