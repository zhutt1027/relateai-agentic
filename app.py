import os
import inspect
import streamlit as st
import json

from core import perception, mediation, memory, schema


# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="HALO (Demo)", layout="wide")
st.title("HALO — Ambient Agent Command Center (Demo)")
st.caption("Constitution → Perception → Mediation → Ledger → Vibe → Decay. (Not therapy.)")


# -------------------------
# Secrets / API key
# -------------------------
def get_api_key():
    # Streamlit Cloud Secrets (TOML): GEMINI_API_KEY="xxxx"
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return os.getenv("GEMINI_API_KEY")


api_key = get_api_key()
if not api_key:
    st.error('Missing GEMINI_API_KEY. Streamlit Secrets must be TOML like:  GEMINI_API_KEY="YOUR_KEY"')
    st.stop()


# -------------------------
# Small helper: pick function by name
# -------------------------
def pick_callable(mod, candidates):
    for name in candidates:
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn, name
    return None, None


def list_callables(mod):
    out = []
    for name in dir(mod):
        if name.startswith("_"):
            continue
        obj = getattr(mod, name)
        if callable(obj):
            out.append(name)
    return sorted(out)


def call_best(fn, **kwargs):
    """
    Call fn with only the kwargs it accepts (so we can pass api_key/model/etc safely).
    """
    sig = inspect.signature(fn)
    accepted = {}
    for k, v in kwargs.items():
        if k in sig.parameters:
            accepted[k] = v
    return fn(**accepted)


# -------------------------
# Defaults
# -------------------------
DEFAULT_CONSTITUTION = """# Household Constitution (Draft)
- "Trash Day" means checking ALL bins: kitchen, bathroom, bedroom, office.
- If someone says "take out the trash", it includes the bathroom bin unless specified otherwise.
- No serious talks while physiologically stressed (pause 5 minutes, then resume).
- When requesting help, use clear task specs: which room(s), by what time.
- Assume good intent; ask one clarifying question before blaming.
"""

DEFAULT_CHAT = """A: You never told me to check the bathroom trash!
B: I thought you meant only the kitchen.
A: We talked about trash day rules already...
"""

if "events" not in st.session_state:
    st.session_state["events"] = None
if "med" not in st.session_state:
    st.session_state["med"] = None
if "ledger" not in st.session_state:
    st.session_state["ledger"] = None
if "vibe" not in st.session_state:
    st.session_state["vibe"] = None
if "decay" not in st.session_state:
    st.session_state["decay"] = None


# -------------------------
# Layout
# -------------------------
left, right = st.columns([1.05, 1.0], gap="large")

with left:
    st.subheader("1) Household Constitution")
    constitution_text = st.text_area("constitution", value=DEFAULT_CONSTITUTION, height=220, label_visibility="collapsed")

    st.subheader("2) Scenario Input (chat)")
    chat_text = st.text_area("chat", value=DEFAULT_CHAT, height=180, label_visibility="collapsed")

    st.subheader("3) Optional context")
    context_text = st.text_area("context", value="", height=90, label_visibility="collapsed")

    model_name = st.text_input("Model name (optional)", value="gemini-2.5-flash")

    run_disabled = (not constitution_text.strip()) or (not chat_text.strip())
    if st.button("▶ Run HALO Loop", type="primary", use_container_width=True, disabled=run_disabled):
        with st.spinner("Running…"):
            # A) Parse constitution (best-effort, optional)
            constitution_obj = {"raw": constitution_text}
            try:
                # if your schema.py exposes a parser, use it; else keep raw
                parse_fn, _ = pick_callable(schema, ["parse_constitution", "parse_rules", "from_text"])
                if parse_fn:
                    constitution_obj = call_best(parse_fn, text=constitution_text, constitution_text=constitution_text)
            except Exception:
                constitution_obj = {"raw": constitution_text}

            # B) Perception
            p_fn, p_name = pick_callable(perception, ["run_perception", "generate_events", "perception", "main"])
            if not p_fn:
                st.error(
                    "Cannot find a perception entrypoint in core/perception.py.\n\n"
                    "Expected one of: run_perception / generate_events / perception / main\n\n"
                    f"Found callables: {list_callables(perception)}"
                )
                st.stop()

            events = call_best(
                p_fn,
                api_key=api_key,
                model=model_name,
                constitution=constitution_obj,
                constitution_text=constitution_text,
                chat=chat_text,
                chat_text=chat_text,
                context=context_text,
                context_text=context_text,
            )
            st.session_state["events"] = events

            # C) Mediation
            m_fn, m_name = pick_callable(mediation, ["run_mediation", "mediate", "mediation", "main"])
            if not m_fn:
                st.error(
                    "Cannot find a mediation entrypoint in core/mediation.py.\n\n"
                    "Expected one of: run_mediation / mediate / mediation / main\n\n"
                    f"Found callables: {list_callables(mediation)}"
                )
                st.stop()

            med = call_best(
                m_fn,
                api_key=api_key,
                model=model_name,
                constitution=constitution_obj,
                constitution_text=constitution_text,
                events=events,
                chat=chat_text,
                chat_text=chat_text,
                context=context_text,
                context_text=context_text,
            )
            st.session_state["med"] = med

            # D) Memory (optional; fallback if your memory.py doesn't implement)
            ledger = None
            vibe = None
            decay = None

            try:
                upsert_fn, _ = pick_callable(memory, ["upsert_receipt", "store_receipt"])
                if upsert_fn:
                    ledger = call_best(upsert_fn, receipt=med, med=med, events=events, constitution=constitution_obj)
            except Exception:
                ledger = None

            try:
                vibe_fn, _ = pick_callable(memory, ["compute_vibe"])
                if vibe_fn:
                    vibe = call_best(vibe_fn, ledger=ledger, state=ledger, window_days=30)
            except Exception:
                vibe = None

            try:
                decay_fn, _ = pick_callable(memory, ["apply_decay", "apply_decay_policy"])
                if decay_fn:
                    decay = call_best(decay_fn, ledger=ledger, state=ledger)
            except Exception:
                decay = None

            # Fallbacks so tabs don't look empty
            st.session_state["ledger"] = ledger if ledger is not None else {"note": "ledger not implemented in memory.py (demo fallback)", "latest": med}
            st.session_state["vibe"] = vibe if vibe is not None else {"note": "vibe not implemented (demo fallback)", "window_days": 30}
            st.session_state["decay"] = decay if decay is not None else {
                "note": "decay not implemented (demo fallback)",
                "tier_1_raw_metadata_48h": True,
                "tier_2_summaries_30d": True,
                "tier_3_embeddings_long_term": True,
            }

        st.success(f"Done. Used perception.{p_name} → mediation.{m_name}")
        st.rerun()


with right:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Perception Events", "Fact Ledger (48h)", "Vibe Score (30d)", "Memory & Decay", "Export"]
    )

    with tab1:
        st.subheader("Perception Events (Simulated)")
        if st.session_state["events"] is None:
            st.info("Run the loop to generate events.")
        else:
            st.json(st.session_state["events"])

    with tab2:
        st.subheader("Fact Ledger (48h)")
        if st.session_state["med"] is None:
            st.info("Run the loop to generate mediation receipt.")
        else:
            st.json(st.session_state["med"])
        st.divider()
        st.caption("Ledger state (optional)")
        st.json(st.session_state["ledger"])

    with tab3:
        st.subheader("Vibe Score (30d)")
        st.json(st.session_state["vibe"])

    with tab4:
        st.subheader("Memory & Decay")
        st.json(st.session_state["decay"])

    with tab5:
        st.subheader("Export")
        bundle = {
            "events": st.session_state["events"],
            "mediation": st.session_state["med"],
            "ledger": st.session_state["ledger"],
            "vibe": st.session_state["vibe"],
            "decay": st.session_state["decay"],
        }
        st.download_button(
            "⬇️ Download JSON bundle",
            data=json.dumps(bundle, ensure_ascii=False, indent=2),
            file_name="halo_bundle.json",
            mime="application/json",
            use_container_width=True,
        )
        st.code(json.dumps(bundle, ensure_ascii=False, indent=2), language="json")
