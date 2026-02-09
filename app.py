import os
import json
import re
import inspect
import streamlit as st

from google import genai

from core import mediation, memory, schema


# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="HALO (Demo)", layout="wide")
st.title("HALO — Relationship Portal v4.2 Command Center (Demo)")
st.caption("Constitution → Perception Events → Mediation → Ledger → Vibe Trend → Memory Decay. (Not therapy.)")


# -------------------------
# Secrets / API key
# -------------------------
def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return os.getenv("GEMINI_API_KEY")


api_key = get_api_key()
if not api_key:
    st.error('Missing GEMINI_API_KEY. Streamlit Secrets must be TOML like:  GEMINI_API_KEY="YOUR_KEY"')
    st.stop()

client = genai.Client(api_key=api_key)


# -------------------------
# Helpers
# -------------------------
def safe_parse_json(text: str):
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None


def pick_callable(mod, candidates):
    for name in candidates:
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn, name
    return None, None


def call_best(fn, **kwargs):
    sig = inspect.signature(fn)
    accepted = {}
    for k, v in kwargs.items():
        if k in sig.parameters:
            accepted[k] = v
    return fn(**accepted)


# -------------------------
# Prompts (Perception in app.py, since core/perception.py has no entrypoint)
# -------------------------
def build_perception_prompt(chat: str, constitution_text: str, context_text: str) -> str:
    return f"""
You are the "Perception Layer" of a neutral home AI system (DEMO).
Given constitution + chat + optional context, produce structured "Perception Events".

Constraints:
- This is a simulation demo. Do NOT invent sensitive personal data.
- Be neutral and non-therapeutic.
- Quotes MUST be copied verbatim from the chat.

Inputs:
CONSTITUTION:
\"\"\"{constitution_text}\"\"\"

CONTEXT (optional):
\"\"\"{context_text}\"\"\"

CHAT:
\"\"\"{chat}\"\"\"

Return STRICT JSON only, schema:
{{
  "events": [
    {{
      "type": "SpeechEvent",
      "timestamp_hint": "unknown|relative",
      "speaker": "A|B|unknown",
      "quote": "verbatim from chat",
      "intent": "request|complaint|defense|clarify|boundary|repair_attempt|other",
      "topic_tags": ["..."],
      "implicit_need": "short"
    }},
    {{
      "type": "TensionSignalEvent",
      "timestamp_hint": "unknown|relative",
      "level": "low|rising|high",
      "signals": ["..."],
      "explanation": "1 sentence neutral"
    }}
  ],
  "notes": {{
    "what_is_simulated": "1 sentence",
    "privacy_statement": "1 sentence"
  }}
}}

Rules:
- Include 3–8 SpeechEvent items (quotes must appear in chat).
- Include exactly 1 TensionSignalEvent.
- STRICT JSON only. No markdown. No extra text.
"""


def gemini_perception(model: str, chat: str, constitution_text: str, context_text: str):
    prompt = build_perception_prompt(chat, constitution_text, context_text)
    resp = client.models.generate_content(model=model, contents=prompt)
    raw = resp.text or ""
    data = safe_parse_json(raw)
    if not data or "events" not in data:
        raise ValueError("Perception did not return valid JSON.")
    return data


# -------------------------
# Defaults / session state
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

for k in ["events", "med", "ledger", "vibe", "decay"]:
    if k not in st.session_state:
        st.session_state[k] = None


# -------------------------
# UI
# -------------------------
left, right = st.columns([1.05, 1.0], gap="large")

with left:
    st.subheader("1) Household Constitution (shared rules)")
    constitution_text = st.text_area("constitution", value=DEFAULT_CONSTITUTION, height=220, label_visibility="collapsed")

    st.subheader("2) Scenario Input (chat)")
    chat_text = st.text_area("chat", value=DEFAULT_CHAT, height=180, label_visibility="collapsed")

    st.subheader("3) Optional context")
    context_text = st.text_area("context", value="", height=90, label_visibility="collapsed")

    model_name = st.text_input("Model", value="gemini-2.5-flash")

    run_disabled = (not constitution_text.strip()) or (not chat_text.strip())
    if st.button("▶ Run HALO Loop", type="primary", use_container_width=True, disabled=run_disabled):
        with st.spinner("Running Perception → Mediation …"):
            # A) Parse constitution (best effort)
            constitution_obj = {"raw": constitution_text}
            try:
                parse_fn, _ = pick_callable(schema, ["parse_constitution_rules", "parse_rules", "from_text"])
                if parse_fn:
                    constitution_obj = call_best(parse_fn, text=constitution_text, constitution_text=constitution_text)
            except Exception:
                constitution_obj = {"raw": constitution_text}

            # B) Perception (implemented here)
            perception_packet = gemini_perception(
                model=model_name,
                chat=chat_text,
                constitution_text=constitution_text,
                context_text=context_text,
                )
            if isinstance(perception_packet, dict) and "events" in perception_packet:
                inner = perception_packet["events"]
                if isinstance(inner, dict) and "events" in inner:
                    events = inner["events"]
                    notes = inner.get("notes", {})
                elif isinstance(inner, list):
                    events = inner
                    notes = {}
                else:
                    events = []
                    notes = {}
            else:
                events = []
                notes = {}
            st.session_state["events"] = events
            st.session_state["perception_notes"] = notes


            # C) Mediation (use your core/mediation.py if it has an entrypoint)
            m_fn, m_name = pick_callable(mediation, ["run_mediation", "mediate", "mediation", "main"])
            if not m_fn:
                # If no entrypoint, fall back to a minimal mediator prompt inside app.py
                # (Still "only app.py change" and keeps app working)
                def fallback_mediation(events_json, constitution_text, chat_text):
                    prompt = f"""
You are a neutral mediator (DEMO, not therapy).
Use events + constitution + chat to produce a Fact Receipt. Be evidence-driven and neutral.

CONSTITUTION:
\"\"\"{constitution_text}\"\"\"

EVENTS JSON:
\"\"\"{json.dumps(events_json, ensure_ascii=False)}\"\"\"

CHAT:
\"\"\"{chat_text}\"\"\"

Return STRICT JSON only:
{{
  "fact_receipt": {{
    "evidence_from_chat": [{{"quote":"...","speaker":"A|B|unknown","why_it_matters":"..."}}],
    "evidence_from_constitution": [{{"rule":"...","why_it_matters":"..."}}]
  }},
  "conclusion": {{"type":"memory_mismatch|rule_mismatch|ambiguous","one_sentence_summary":"..."}},
  "suggestions": {{
    "for_A": ["..."],
    "for_B": ["..."],
    "rule_update_proposal": "..."
  }},
  "quiet_warning": {{
    "should_notify": true,
    "notify_target": "A|B|both",
    "message": "..."
  }}
}}
Rules:
- Evidence quotes MUST be verbatim from chat (or from SpeechEvent.quote).
- Constitution rules MUST be excerpts from constitution text.
- STRICT JSON only.
"""
                    resp = client.models.generate_content(model=model_name, contents=prompt)
                    raw = resp.text or ""
                    out = safe_parse_json(raw)
                    if not out:
                        raise ValueError("Fallback mediation returned invalid JSON.")
                    return out, "fallback_mediation"

                med, m_name = fallback_mediation(events, constitution_text, chat_text)
            else:
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

            # D) Memory (optional)
            ledger = vibe = decay = None
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

            st.session_state["ledger"] = ledger if ledger is not None else {"note": "ledger not implemented (fallback)", "latest": med}
            st.session_state["vibe"] = vibe if vibe is not None else {"note": "vibe not implemented (fallback)", "window_days": 30}
            st.session_state["decay"] = decay if decay is not None else {
                "note": "decay not implemented (fallback)",
                "tier_1_raw_metadata_48h": True,
                "tier_2_summaries_30d": True,
                "tier_3_embeddings_long_term": True,
            }

        st.success("Done.")
        st.rerun()


with right:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Perception Events", "Fact Ledger (48h)", "Vibe Score (30d)", "Memory & Decay", "Export"]
    )

    with tab1:
        st.subheader("Perception Events (Simulated)")
        if st.session_state["events"] is None:
            st.info("Run HALO loop to generate perception events.")
        else:
            st.json(st.session_state["events"])

    with tab2:
        st.subheader("Fact Receipt / Ledger (48h)")
        if st.session_state["med"] is None:
            st.info("Run HALO loop to generate mediation receipt.")
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
