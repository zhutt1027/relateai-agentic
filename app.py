import os
import json
from dataclasses import asdict
from typing import Any, Dict, Optional

import streamlit as st
from dotenv import load_dotenv
from google import genai

from core.prompts import sensor_prompt, mediator_prompt
from core.perception import safe_parse_json, parse_constitution_rules, extract_tension_level
from core.memory import utc_now_iso, add_run_artifacts, apply_retention_policy, export_payload
from core.schema import LedgerEntry, VibePoint, Tier1Record, Tier2Summary, Tier3Embedding

# -------------------------
# App Config
# -------------------------
load_dotenv()
st.set_page_config(page_title="HALO — Ambient Agent Demo", layout="wide")
st.title("HALO — Ambient Agent Command Center (Demo)")
st.caption("Constitution → Perception Events → Mediation → Ledger → Vibe Trend → Memory Decay. (Not therapy.)")

# -------------------------
# Secrets / Client
# -------------------------
def get_api_key() -> Optional[str]:
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return os.getenv("GEMINI_API_KEY")

api_key = get_api_key()
if not api_key:
    st.error("Missing GEMINI_API_KEY. Add it to Streamlit Secrets (TOML) or local .env.")
    st.stop()

client = genai.Client(api_key=api_key)

# -------------------------
# Session State
# -------------------------
def ensure_state():
    if "model_name" not in st.session_state:
        st.session_state.model_name = "gemini-2.5-flash"

    if "ledger_48h" not in st.session_state:
        st.session_state.ledger_48h = []  # List[LedgerEntry]

    if "vibe_history" not in st.session_state:
        st.session_state.vibe_history = []  # List[VibePoint]

    if "tier1_events_48h" not in st.session_state:
        st.session_state.tier1_events_48h = []  # List[Tier1Record]

    if "tier2_summaries_30d" not in st.session_state:
        st.session_state.tier2_summaries_30d = []  # List[Tier2Summary]

    if "tier3_embeddings" not in st.session_state:
        st.session_state.tier3_embeddings = []  # List[Tier3Embedding]

    if "last_events" not in st.session_state:
        st.session_state.last_events = None

    if "last_result" not in st.session_state:
        st.session_state.last_result = None

ensure_state()

# -------------------------
# Sidebar Controls
# -------------------------
with st.sidebar:
    st.header("Run Controls")
    st.session_state.model_name = st.text_input("Model", value=st.session_state.model_name)
    perception_mode = st.selectbox("Perception mode", ["demo_mock", "conservative"], index=0)

    st.markdown("---")
    st.subheader("Privacy Controls (Demo)")
    show_raw_chat = st.checkbox("Show raw chat on screen (demo only)", value=True)
    store_raw_chat = st.checkbox(
        "Store raw chat (NOT recommended)",
        value=False,
        help="Keep OFF. Proposal says no raw audio/video; raw chat also should not be stored.",
    )

    st.markdown("---")
    if st.button("🧹 Clear session (demo reset)"):
        for k in list(st.session_state.keys()):
            if k not in ("model_name",):
                del st.session_state[k]
        ensure_state()
        st.success("Session cleared.")

# -------------------------
# Main Layout
# -------------------------
col_left, col_right = st.columns([1.05, 1])

with col_left:
    st.subheader("1) Household Constitution (shared rules)")
    default_constitution = """# Household Constitution (Draft)
- "Trash Day" means checking ALL bins: kitchen, bathroom, bedroom, office.
- If someone says "take out the trash", it includes the bathroom bin unless specified otherwise.
- No serious talks while physiologically stressed (pause 5 minutes, then resume).
- When requesting help, use clear task specs: which room(s), by what time.
- Assume good intent; ask one clarifying question before blaming.
"""
    constitution = st.text_area("Constitution", value=default_constitution, height=220)

    st.subheader("2) Scenario Input (chat)")
    chat_text = st.text_area(
        "Paste chat (A: ... / B: ...)",
        height=220,
        placeholder="A: You never told me to check the bathroom trash!\nB: I thought you meant only the kitchen.\nA: We talked about trash day rules already..."
    )

    st.subheader("3) Optional Context (for richer mock sensing)")
    context_notes = st.text_area(
        "Context (optional)",
        height=90,
        placeholder='e.g., "Evening, kitchen. One partner cleaning, other on couch. Apple Watch available."'
    )

    run = st.button("▶ Run HALO Loop (Perception → Mediation)", type="primary", disabled=(len(chat_text.strip()) == 0))

with col_right:
    st.subheader("Command Center")
    rules_list = parse_constitution_rules(constitution)
    st.write("Parsed rules (quick view):")
    st.json({"rules": rules_list})

    st.markdown("---")
    tabs = st.tabs(["Perception Events", "Fact Ledger (48h)", "Vibe Score (30d)", "Memory & Decay", "Export"])

# -------------------------
# Run Loop
# -------------------------
if run:
    if store_raw_chat:
        st.warning("Raw chat storage is ON (demo). Proposal recommends storing only derived events, not raw chat/audio/video.")

    # Stage 1: Perception
    with st.spinner("Stage 1/2: Generating perception events (simulated sensors)…"):
        p1 = sensor_prompt(chat=chat_text, constitution=constitution, context_notes=context_notes, mode=perception_mode)
        r1 = client.models.generate_content(model=st.session_state.model_name, contents=p1)
        events = safe_parse_json(r1.text or "")

    if not events or "events" not in events:
        with tabs[0]:
            st.error("Perception failed: model did not return valid JSON.")
            st.code(r1.text or "")
        st.stop()

    st.session_state.last_events = events

    # Stage 2: Mediation
    with st.spinner("Stage 2/2: Mediating with constitution + evidence…"):
        p2 = mediator_prompt(events_json=events, constitution=constitution)
        r2 = client.models.generate_content(model=st.session_state.model_name, contents=p2)
        result = safe_parse_json(r2.text or "")

    if not result:
        with tabs[0]:
            st.error("Mediation failed: model did not return valid JSON.")
            st.code(r2.text or "")
        st.stop()

    st.session_state.last_result = result

    # Store derived artifacts
    ts = utc_now_iso()
    tension_level, _hint = extract_tension_level(events)

    add_run_artifacts(
        ts=ts,
        events=events,
        result=result,
        ledger_48h=st.session_state.ledger_48h,
        vibe_history=st.session_state.vibe_history,
        tier1_events_48h=st.session_state.tier1_events_48h,
        tier2_summaries_30d=st.session_state.tier2_summaries_30d,
        tier3_embeddings=st.session_state.tier3_embeddings,
        tension_level=tension_level,
    )

    apply_retention_policy(
        ledger_48h=st.session_state.ledger_48h,
        vibe_history=st.session_state.vibe_history,
        tier1_events_48h=st.session_state.tier1_events_48h,
        tier2_summaries_30d=st.session_state.tier2_summaries_30d,
        tier3_embeddings=st.session_state.tier3_embeddings,
    )

# -------------------------
# Render Tabs (always show last known)
# -------------------------
with tabs[0]:
    st.subheader("Perception Events (Simulated)")
    st.caption("Structured events derived from chat + constitution. Sensor signals may be simulated for demo.")
    if st.session_state.last_events:
        st.json(st.session_state.last_events)
    else:
        st.info("Run the loop to generate perception events.")

with tabs[1]:
    st.subheader("Fact Ledger (48h Truth Buffer)")
    st.caption("Stores derived facts only (quotes + constitution excerpts). No raw audio/video stored.")
    if st.session_state.ledger_48h:
        latest: LedgerEntry = st.session_state.ledger_48h[0]
        st.markdown(f"### Latest Entry — {latest.ts_utc}")
        st.json(asdict(latest))

        with st.expander("Show recent entries (up to 10)"):
            for i, e in enumerate(st.session_state.ledger_48h[:10], start=1):
                st.markdown(f"**{i}. {e.ts_utc}**")
                st.write(f"- conclusion: `{e.conclusion.get('type','')}`")
                plan = e.intervention_plan or {}
                st.write(f"- notify: **{plan.get('should_notify', False)}** via `{plan.get('channel','none')}`")
    else:
        st.info("No ledger entries yet. Run the loop.")

with tabs[2]:
    st.subheader("Vibe Score (30-day trend, demo)")
    if st.session_state.vibe_history:
        latest: VibePoint = st.session_state.vibe_history[-1]
        st.metric("Latest tension level", latest.level)
        st.metric("Last run: should notify", "Yes" if latest.notify else "No")

        map_level = {"low": 1, "rising": 2, "high": 3, "unknown": 0}
        series = [map_level.get(v.level, 0) for v in st.session_state.vibe_history[-60:]]
        st.line_chart(series)
        st.caption("Chart: 0=unknown, 1=low, 2=rising, 3=high (demo).")
    else:
        st.info("No vibe history yet. Run the loop.")

with tabs[3]:
    st.subheader("Memory & Decay Pipeline (Demo)")
    st.write("Tier 1: structured event metadata (48h) → Tier 2: summaries (30d) → Tier 3: embeddings (long-term)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tier 1 (48h)", len(st.session_state.tier1_events_48h))
    c2.metric("Tier 2 (30d)", len(st.session_state.tier2_summaries_30d))
    c3.metric("Tier 3 (embeddings)", len(st.session_state.tier3_embeddings))

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("Apply Decay Now (clear Tier 1)"):
            st.session_state.tier1_events_48h = []
            st.success("Tier 1 cleared (demo).")
    with colB:
        if st.button("Prune to policy (48h / 30d)"):
            apply_retention_policy(
                ledger_48h=st.session_state.ledger_48h,
                vibe_history=st.session_state.vibe_history,
                tier1_events_48h=st.session_state.tier1_events_48h,
                tier2_summaries_30d=st.session_state.tier2_summaries_30d,
                tier3_embeddings=st.session_state.tier3_embeddings,
            )
            st.success("Retention policy applied.")

    st.markdown("### Tier 1 (sample)")
    st.json([asdict(x) for x in st.session_state.tier1_events_48h[:2]])

    st.markdown("### Tier 2 (sample)")
    st.json([asdict(x) for x in st.session_state.tier2_summaries_30d[:5]])

    st.markdown("### Tier 3 (sample)")
    st.json([asdict(x) for x in st.session_state.tier3_embeddings[:8]])

with tabs[4]:
    st.subheader("Export")
    st.caption("Export derived artifacts only (no raw chat/audio/video).")

    payload = export_payload(
        ledger_48h=st.session_state.ledger_48h,
        vibe_history=st.session_state.vibe_history,
        tier2_summaries_30d=st.session_state.tier2_summaries_30d,
        tier3_embeddings=st.session_state.tier3_embeddings,
    )

    st.download_button(
        "Download HALO demo export (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2),
        file_name="halo_demo_export.json",
        mime="application/json"
    )

    if st.session_state.last_result:
        st.markdown("### Latest intervention plan (quick copy)")
        plan = st.session_state.last_result.get("intervention_plan", {})
        st.code(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        st.info("Run the loop to generate an export.")
