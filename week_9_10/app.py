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
    "LEGO-001": {
        "stock": 250,
        "reserved": 40,
        "restock_date": "2026-05-20",
        "warehouse": "Mumbai-WH1",
    },
    "LEGO-002": {
        "stock": 80,
        "reserved": 10,
        "restock_date": "2026-05-15",
        "warehouse": "Mumbai-WH1",
    },
    "LEGO-003": {
        "stock": 15,
        "reserved": 5,
        "restock_date": "2026-05-25",
        "warehouse": "Mumbai-WH2",
    },
}

DISCOUNT_RULES = [
    {"min_qty": 100, "discount_pct": 20, "label": "Bulk (100+)"},
    {"min_qty": 50, "discount_pct": 10, "label": "Volume (50-99)"},
    {"min_qty": 20, "discount_pct": 5, "label": "Standard (20-49)"},
    {"min_qty": 0, "discount_pct": 0, "label": "No discount (<20)"},
]

# ─────────────────────────────────────────────────────────────────────────────
# LangChain Tools
# ─────────────────────────────────────────────────────────────────────────────


@tool
def get_product_info(product_id: str) -> dict:
    """Retrieve full product details (name, brand, unit price, category) for a given product ID.
    Available IDs: LEGO-001, LEGO-002, LEGO-003."""
    product = PRODUCT_DB.get(product_id.upper())
    if not product:
        return {
            "error": f"Product '{product_id}' not found.",
            "available_ids": list(PRODUCT_DB.keys()),
        }
    return {"status": "ok", "product": product}


@tool
def check_inventory(product_id: str) -> dict:
    """Check current Week 3 stock levels for a product.
    Returns available qty, reserved stock, restock date, and warehouse."""
    inv = INVENTORY_DB.get(product_id.upper())
    if not inv:
        return {"error": f"No inventory record for '{product_id}'."}
    available = inv["stock"] - inv["reserved"]
    return {
        "status": "ok",
        "product_id": product_id.upper(),
        "total_stock": inv["stock"],
        "reserved": inv["reserved"],
        "available": available,
        "restock_date": inv["restock_date"],
        "warehouse": inv["warehouse"],
        "week": "Week 3",
        "in_stock": available > 0,
    }


@tool
def calculate_quote(product_id: str, quantity: int) -> dict:
    """Calculate a price quote with tiered discounts + 18% GST.
    Tiers: qty>=100→20% off, qty>=50→10% off, qty>=20→5% off, qty<20→0% off."""
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
        "status": "ok",
        "product_id": product_id.upper(),
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price_usd": round(unit_price, 2),
        "subtotal_usd": round(subtotal, 2),
        "discount_tier": rule["label"],
        "discount_pct": rule["discount_pct"],
        "discount_amount_usd": round(discount_amt, 2),
        "discounted_subtotal_usd": round(discounted, 2),
        "tax_rate_pct": 18,
        "tax_amount_usd": round(tax_amt, 2),
        "grand_total_usd": round(grand_total, 2),
        "currency": "USD",
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
# Agent builder (cached so it's not rebuilt on every rerun)
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_resource
def build_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # 1. Initialize the checkpointer for memory
    memory = InMemorySaver()
    # 2. Attach memory to the agent
    return create_agent(llm, TOOLS, system_prompt=SYSTEM_PROMPT, checkpointer=memory)


def run_agent(user_request: str, thread_id: str, log_callback=None):
    agent = build_agent()

    # 3. Configure the thread ID for memory lookup
    config = {"configurable": {"thread_id": thread_id}}

    # 4. Invoke the agent with the config
    result = agent.invoke(
        {"messages": [HumanMessage(content=user_request)]}, config=config
    )

    # Surface tool calls to the UI
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
# Streamlit UI
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Quote Agent", page_icon="🧱", layout="wide")

# 5. Initialize Thread ID in Streamlit session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.hero-title { font-family:'Syne',sans-serif; font-size:2.8rem; font-weight:800;
              letter-spacing:-1px; color:#ffffff; line-height:1.1; margin-bottom:.25rem; }
.hero-sub   { font-size:1.05rem; color:#64748b; margin-bottom:2rem; }
.inv-card   { background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%); border-radius:16px;
              padding:28px 32px; color:#f8fafc; box-shadow:0 20px 60px rgba(15,23,42,.25); }
.inv-hdr    { display:flex; justify-content:space-between; align-items:flex-start;
              margin-bottom:24px; border-bottom:1px solid rgba(255,255,255,.1); padding-bottom:16px; }
.inv-title  { font-family:'Syne',sans-serif; font-size:1.5rem; font-weight:800; color:#f59e0b; }
.inv-num    { font-size:.8rem; color:#94a3b8; }
.inv-row    { display:flex; justify-content:space-between; padding:6px 0; font-size:.95rem; }
.inv-label  { color:#94a3b8; }
.inv-val    { color:#f8fafc; font-weight:500; }
.inv-divider{ border-top:1px solid rgba(255,255,255,.08); margin:12px 0; }
.inv-total  { font-family:'Syne',sans-serif; font-size:1.6rem; font-weight:800; color:#34d399; }
.inv-note   { margin-top:18px; padding:12px 16px; background:rgba(245,158,11,.1);
              border-left:3px solid #f59e0b; border-radius:6px; font-size:.9rem; color:#fde68a; }
.tool-log   { background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
              padding:10px 14px; margin:6px 0; font-size:.83rem; }
.badge      { display:inline-block; padding:2px 10px; border-radius:999px;
              font-size:.75rem; font-weight:600; background:#dbeafe; color:#1d4ed8; }
.disc-badge { background:#dcfce7; color:#15803d; }
.model-chip { display:inline-block; padding:3px 10px; border-radius:999px; font-size:.75rem;
              background:#f1f5f9; color:#475569; margin-left:8px; border:1px solid #e2e8f0; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Check API key ─────────────────────────────────────────────────────────────
if not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️  `OPENAI_API_KEY` not found. Set it in your environment and restart.")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero-title">🧱 Product Quote Agent</div>', unsafe_allow_html=True
)
st.markdown(
    '<div class="hero-sub">LangChain · LangGraph ReAct · OpenAI gpt-4o-mini '
    '<span class="model-chip">gpt-4o-mini</span></div>',
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📦 Product Catalog")
    for pid, p in PRODUCT_DB.items():
        inv = INVENTORY_DB[pid]
        avail = inv["stock"] - inv["reserved"]
        st.markdown(f"""
**{p['emoji']} {p['name']}**  
`{pid}` · ${p['unit_price']:.2f}/unit  
Stock (Wk3): **{avail}** available
""")
        st.divider()

    st.markdown("### 💰 Discount Tiers")
    for rule in DISCOUNT_RULES:
        if rule["discount_pct"] > 0:
            st.markdown(f"- **{rule['discount_pct']}% off** — {rule['label']}")
    st.markdown("- No discount for orders < 20 units")
    st.caption("+ 18% GST on all orders")

    st.markdown("### 🔗 LangChain Stack")
    st.caption("langchain-openai · langgraph · langchain-core")

    # Optional UI element to reset the chat memory
    if st.button("Reset Conversation", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.success("Conversation reset!")

# ── Main layout ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1.1, 1], gap="large")

with col_left:
    st.markdown("#### 💬 Your Request")
    examples = [
        "I need 60 building blocks for a school project, can I get a deal?",
        "We want to order 120 Duplo starter kits for a chain of preschools.",
        "How much for 30 Technic Gear Packs for a robotics club?",
    ]
    selected = st.selectbox("Quick examples", ["— select or type below —"] + examples)
    user_input = st.text_area(
        "Or type your own:",
        value=selected if selected != "— select or type below —" else "",
        height=100,
        placeholder="e.g. I need 60 building blocks for a school project, can I get a deal?",
    )
    run_btn = st.button("🚀 Generate Quote", type="primary", use_container_width=True)

with col_right:
    st.markdown("#### 🔧 Agent Tool Calls")
    log_placeholder = st.empty()
    logs = []

if run_btn and user_input.strip():
    with col_right:
        log_placeholder.info("⏳ Agent is thinking…")

    tool_log_html = ""

    def log_tool(name, inputs, result):
        icon = {
            "get_product_info": "📋",
            "check_inventory": "📊",
            "calculate_quote": "💵",
        }.get(name, "🔧")
        logs.append({"name": name, "inputs": inputs, "result": result})

        # 6. FIXED: Changed nonlocal to global
        global tool_log_html

        snippet = json.dumps(result)
        tool_log_html += (
            f'<div class="tool-log">{icon} <strong>{name}</strong><br>'
            f'<span style="color:#64748b">Input:</span> <code>{json.dumps(inputs)}</code><br>'
            f'<span style="color:#64748b">→</span> {snippet[:150]}{"…" if len(snippet)>150 else ""}</div>'
        )
        log_placeholder.markdown(tool_log_html, unsafe_allow_html=True)

    try:
        # 7. Pass the thread_id to the agent runner
        invoice = run_agent(
            user_input.strip(),
            thread_id=st.session_state.thread_id,
            log_callback=log_tool,
        )
    except Exception as e:
        st.error(f"Agent error: {e}")
        st.stop()

    with col_left:
        st.markdown("#### 📄 Quote Invoice")
        if "raw_response" in invoice:
            st.markdown(invoice["raw_response"])
        else:
            # Extract fields defensively from nested or flat JSON
            pricing = invoice.get("pricing", invoice)
            product = invoice.get("product", {})
            inv_inf = invoice.get("inventory", {})

            pname = product.get("name") or invoice.get("product_name", "—")
            pid_val = product.get("id") or invoice.get("product_id", "—")
            avail = inv_inf.get("available_stock") or "—"
            wh = inv_inf.get("warehouse") or "—"
            qty = pricing.get("quantity", "—")
            unit_p = pricing.get("unit_price", "—")
            sub = pricing.get("subtotal", "—")
            disc_p = pricing.get("discount_pct", 0)
            disc_a = pricing.get("discount_amount", "—")
            tax_a = pricing.get("tax_amount", "—")
            total = pricing.get("grand_total", "—")
            note = invoice.get("friendly_note", "")
            inv_num = invoice.get(
                "invoice_number", f"INV-{datetime.today().strftime('%Y%m%d')}-001"
            )

            st.markdown(
                f"""
<div class="inv-card">
  <div class="inv-hdr">
    <div>
      <div class="inv-title">QUOTE INVOICE</div>
      <div class="inv-num">{inv_num} &nbsp;·&nbsp; {datetime.today().strftime('%d %b %Y')}</div>
    </div>
    <div style="text-align:right">
      <div style="font-size:.85rem;color:#94a3b8">Product</div>
      <div style="font-weight:600">{pname}</div>
      <div style="font-size:.8rem;color:#64748b">{pid_val} · {wh}</div>
    </div>
  </div>
  <div class="inv-row"><span class="inv-label">Quantity</span><span class="inv-val">{qty} units</span></div>
  <div class="inv-row"><span class="inv-label">Unit price</span><span class="inv-val">${unit_p}</span></div>
  <div class="inv-row"><span class="inv-label">Subtotal</span><span class="inv-val">${sub}</span></div>
  <div class="inv-divider"></div>
  <div class="inv-row"><span class="inv-label">Discount <span class="disc-badge">{disc_p}% off</span></span><span class="inv-val" style="color:#34d399">− ${disc_a}</span></div>
  <div class="inv-row"><span class="inv-label">GST (18%)</span><span class="inv-val">${tax_a}</span></div>
  <div class="inv-divider"></div>
  <div class="inv-row"><span class="inv-label" style="font-size:1rem;font-weight:600;color:#f8fafc">GRAND TOTAL</span><span class="inv-total">${total}</span></div>
  <div class="inv-row"><span class="inv-label">📦 Stock (Week 3)</span><span class="inv-val badge">{avail} units</span></div>
  {f'<div class="inv-note">💬 {note}</div>' if note else ''}
</div>
""",
                unsafe_allow_html=True,
            )

            st.markdown("##### Raw JSON")
            st.json(invoice)

elif run_btn:
    st.warning("Please enter a request first.")
