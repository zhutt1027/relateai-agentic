# HALO — Relationship Portal v4.2 Command Center（Demo)

> Gemini simulates perception → reasons with shared rules → produces evidence-based mediation.
> **Not therapy. A neutral, agentic memory system for relationships.**

---

## 🧠 The Idea

Arguments are rarely about the task.
They are about **what each person believes happened**.

HALO introduces a **third neutral entity** into the room —
not a spy, not a judge — but a system that:

1. Interprets conversations as structured **Perception Events**
2. Applies a shared **Household Constitution**
3. Produces an objective **Fact Receipt**
4. Maintains a short-term **Ledger (48h)**
5. Simulates long-term **Memory & Decay**
6. (Future) Detects tension trends and gives proactive nudges

HALO does not decide who is right.
HALO shows **what happened relative to agreed rules**.

---

## 🏗️ Architecture (Agentic Design)

```
Chat + Constitution
        ↓
Perception Agent (Gemini)
        ↓
Structured Events
        ↓
Mediation Agent (Gemini)
        ↓
Fact Receipt
        ↓
Ledger / Memory / Vibe / Decay
```

The system is intentionally modular:

| Module          | Responsibility                    |
| --------------- | --------------------------------- |
| `perception.py` | Turns chat into structured events |
| `mediation.py`  | Reasons over events + rules       |
| `memory.py`     | Simulates ledger / decay layers   |
| `schema.py`     | Shared JSON contracts             |
| `prompts.py`    | All Gemini reasoning prompts      |
| `app.py`        | HALO orchestration UI             |

---

## 🖥️ Demo Flow (What the app does)

1. Define a **Household Constitution** (shared rules)
2. Paste a chat scenario
3. Run **HALO Loop**
4. View:

* Perception Events
* Fact Ledger (48h)
* Vibe Score (placeholder)
* Memory & Decay model
* Export full JSON bundle

---

## 🔐 Privacy by Design

HALO never stores raw video, audio, or identity.

It stores only:

* Semantic events
* Rule alignment
* Derived summaries
* (Future) vector embeddings for pattern coaching

This mimics a real-world privacy-first sensing system.

---

## 🚀 Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Create a `.env` file:

```
GEMINI_API_KEY=AIzaSyCHMOJfY-41_-nL6O8ovCX2yloMsLqYo1k
```

---

## ☁️ Live Demo

Deployed on Streamlit Cloud.

Every push to `main` auto-updates the demo.

---

## 🧩 Why This Is Interesting

Most AI chat apps respond to text.
HALO simulates a **multi-agent system** with memory, rules, and evidence.

This is closer to how future ambient AI systems will behave:

* Persistent
* Context-aware
* Rule-aligned
* Privacy-preserving

---

## ⚠️ Disclaimer

This is a **technical demo** of an agent architecture.
Not therapy. Not relationship advice.

---

## 👥 Collaboration

We follow a feature-branch workflow:

```
git checkout -b feature/xyz
git commit
git push
Pull Request → Review → Merge
```

---

## 📦 Export

The Export tab provides the full JSON trace of:

* Events
* Mediation
* Ledger
* Memory
* Vibe
* Decay

Useful for debugging, research, or evaluation.

---

## 💡 Future Work

* Real sensor integration (HealthKit / Camera)
* Tension prediction model
* Long-term embedding memory
* Wearable nudges

---

**HALO is a prototype for how AI can mediate human memory — neutrally, transparently, and respectfully.**
