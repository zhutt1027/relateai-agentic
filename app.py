import os
import re
import json
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()

st.set_page_config(page_title="RelateAI", layout="centered")
st.title("RelateAI — Agentic Neutral Black Box (Demo)")
st.caption("Gemini simulates perception events → Gemini mediates with evidence (Not therapy).")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("Missing GEMINI_API_KEY. Put it in a .env file.")
    st.stop()

client = genai.Client(api_key=api_key)

MODEL_NAME = "gemini-2.5-flash"

# -------------------------
# Helpers
# -------------------------
def safe_parse_json(text: str):
    """Try to parse JSON even if model accidentally wraps it with extra text."""
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

def build_sensor_prompt(chat: str, manual: str) -> str:
    """
    Gemini #1: simulate events like sensors (Recorder/Vision/Tension)
    """
    return f"""
You are the "Perception Layer" of a home-neutral AI system.
Given household manual + chat, simulate the events that a real system would produce.
Important: This is a DEMO simulation. Do NOT invent sensitive personal data.
Be neutral and non-therapeutic.

Household Manual:
\"\"\"{manual}\"\"\"

Chat history:
\"\"\"{chat}\"\"\"

Return STRICT JSON only with this schema:
{{
  "events": [
    {{
      "type": "SpeechEvent",
      "timestamp_hint": "e.g., Tue 7pm or unknown",
      "speaker": "A|B|unknown",
      "quote": "direct quote from the chat",
      "thought_signature": {{
        "intent": "request|complaint|defense|clarify|boundary|repair_attempt|other",
        "topic_tags": ["trash","chores","tone","time","fairness"],
        "implicit_need": "short neutral phrase"
      }}
    }},
    {{
      "type": "VisionTaskEvent",
      "timestamp_hint": "optional",
      "task": "kitchen_trash|bathroom_trash|dishes|laundry|other",
      "state": "done|not_done|unknown",
      "confidence": 0.0
    }},
    {{
      "type": "TensionSignalEvent",
      "timestamp_hint": "optional",
      "level": "low|rising|high",
      "signals": ["absolute_language","blame","sarcasm","rapid_escalation","exclamation","questioning"],
      "explanation": "1 sentence, neutral"
    }}
  ],
  "notes": {{
    "what_is_simulated": "1 sentence explaining these events are simulated for demo",
    "privacy_statement": "1 sentence about storing only derived states, not raw video"
  }}
}}

Rules:
- Include 3-8 SpeechEvent items from the chat (quotes must appear in chat).
- Include 1-3 VisionTaskEvent items that are plausible given the chat + manual (state can be 'unknown').
- Include exactly 1 TensionSignalEvent summarizing escalation risk.
- STRICT JSON only. No markdown. No extra text.
"""

def build_mediator_prompt(events_json: dict, manual: str) -> str:
    """
    Gemini #2: mediator reasoning using events + manual → Fact Receipt + notice decision
    """
    events_text = json.dumps(events_json, ensure_ascii=False)
    return f"""
You are the "Mediator / Reasoning Engine" of a neutral home AI.
Use the events (simulated perception) + Household Manual to produce a Fact Receipt.
Focus on evidence and rule alignment. Non-therapeutic. No diagnosis.

Household Manual:
\"\"\"{manual}\"\"\"

Simulated Events JSON:
\"\"\"{events_text}\"\"\"

Return STRICT JSON only with this schema:
{{
  "fact_receipt": {{
    "evidence_from_chat": [
      {{
        "quote": "direct quote (from SpeechEvent.quote)",
        "speaker": "A|B|unknown",
        "why_it_matters": "short neutral explanation"
      }}
    ],
    "evidence_from_manual": [
      {{
        "rule": "direct excerpt from manual",
        "why_it_matters": "short"
      }}
    ]
  }},
  "conclusion": {{
    "type": "memory_mismatch|rule_mismatch|ambiguous",
    "one_sentence_summary": "neutral"
  }},
  "suggestions": {{
    "for_A": ["2-3 concrete actions, respectful"],
    "for_B": ["2-3 concrete actions, respectful"],
    "rule_update_proposal": "one proposed updated rule in plain language"
  }},
  "quiet_warning": {{
    "should_notify": true,
    "notify_target": "A|B|both",
    "message": "private nudge message, 1-2 sentences, actionable"
  }}
}}

Rules:
- Evidence quotes MUST come from SpeechEvent.quote.
- Manual rules MUST be excerpts from the given manual text.
- Conclusion must pick ONE of the 3 types and justify neutrally.
- Suggestions must be concrete and practical.
- STRICT JSON only. No markdown. No extra text.
"""

# -------------------------
# UI inputs
# -------------------------
default_manual = """Household Manual (Draft)
- "Trash Day" means checking ALL bins: kitchen, bathroom, bedroom, office.
- If someone says "take out the trash", it includes the bathroom bin unless specified otherwise.
- When requesting help, prefer clear task specs: which room(s), by what time.
"""

manual = st.text_area("Household Manual (shared rules)", value=default_manual, height=160)

chat_text = st.text_area(
    "Paste chat history (format like A: ... / B: ...)",
    height=260,
    placeholder="A: You never told me to check the bathroom trash!\nB: I thought you meant only the kitchen.\nA: We talked about trash day rules already..."
)

# -------------------------
# Run Agentic demo (2-stage)
# -------------------------
if st.button("Analyze (Agentic)", type="primary", disabled=(len(chat_text.strip()) == 0)):
    # ---- Stage 1: Simulate events ----
    with st.spinner("Stage 1/2: Gemini simulating perception events..."):
        sensor_prompt = build_sensor_prompt(chat_text, manual)
        resp1 = client.models.generate_content(model=MODEL_NAME, contents=sensor_prompt)
        raw1 = resp1.text or ""
        events = safe_parse_json(raw1)

    if not events or "events" not in events:
        st.error("Stage 1 failed: Gemini did not return valid events JSON.")
        st.code(raw1)
        st.stop()

    st.subheader("🛰️ Simulated Events (Perception Layer)")
    st.json(events)

    # ---- Stage 2: Mediate with evidence ----
    with st.spinner("Stage 2/2: Gemini mediating with evidence..."):
        mediator_prompt = build_mediator_prompt(events, manual)
        resp2 = client.models.generate_content(model=MODEL_NAME, contents=mediator_prompt)
        raw2 = resp2.text or ""
        result = safe_parse_json(raw2)

    if not result:
        st.error("Stage 2 failed: Gemini did not return valid mediation JSON.")
        st.code(raw2)
        st.stop()

    # -------------------------
    # Render results nicely
    # -------------------------
    st.subheader("🧾 Fact Receipt")
    fr = result.get("fact_receipt", {})
    chat_ev = fr.get("evidence_from_chat", [])
    man_ev = fr.get("evidence_from_manual", [])

    st.write("**Evidence from chat**")
    if chat_ev:
        for e in chat_ev:
            st.write(f"- ({e.get('speaker','?')}) “{e.get('quote','')}” — {e.get('why_it_matters','')}")
    else:
        st.write("- (none)")

    st.write("**Evidence from household manual**")
    if man_ev:
        for e in man_ev:
            st.write(f"- “{e.get('rule','')}” — {e.get('why_it_matters','')}")
    else:
        st.write("- (none)")

    st.subheader("✅ Conclusion")
    con = result.get("conclusion", {})
    st.write(f"**Type:** `{con.get('type','')}`")
    st.write(con.get("one_sentence_summary", ""))

    st.subheader("💡 Suggestions")
    sug = result.get("suggestions", {})
    st.write("**For Partner A**")
    for s in sug.get("for_A", []):
        st.write(f"- {s}")
    st.write("**For Partner B**")
    for s in sug.get("for_B", []):
        st.write(f"- {s}")

    st.write("**Rule update proposal**")
    if sug.get("rule_update_proposal"):
        st.info(sug.get("rule_update_proposal"))

    st.subheader("⚠️ Quiet Warning")
    qw = result.get("quiet_warning", {})
    st.write(f"Should notify: **{qw.get('should_notify', False)}**")
    st.write(f"Target: **{qw.get('notify_target', 'unknown')}**")
    st.write(qw.get("message", ""))