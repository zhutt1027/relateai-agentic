# ledger / vibe / decay
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .schema import LedgerEntry, VibePoint, Tier1Record, Tier2Summary, Tier3Embedding


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def make_fake_embedding_id(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def prune_by_hours(items: List[Any], hours: int, ts_attr: str = "ts_utc", keep_max: int = 5000) -> List[Any]:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    kept = []
    for it in items:
        ts = getattr(it, ts_attr, "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", ""))
            if dt >= cutoff:
                kept.append(it)
        except Exception:
            kept.append(it)
    return kept[:keep_max]


def prune_by_days(items: List[Any], days: int, ts_attr: str = "ts_utc", keep_max: int = 5000) -> List[Any]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    kept = []
    for it in items:
        ts = getattr(it, ts_attr, "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", ""))
            if dt >= cutoff:
                kept.append(it)
        except Exception:
            kept.append(it)
    return kept[:keep_max]


def add_run_artifacts(
    *,
    ts: str,
    events: Dict[str, Any],
    result: Dict[str, Any],
    ledger_48h: List[LedgerEntry],
    vibe_history: List[VibePoint],
    tier1_events_48h: List[Tier1Record],
    tier2_summaries_30d: List[Tier2Summary],
    tier3_embeddings: List[Tier3Embedding],
    tension_level: str,
) -> None:
    # Ledger (derived-only)
    entry = LedgerEntry(
        ts_utc=ts,
        fact_receipt=result.get("fact_receipt", {}),
        conclusion=result.get("conclusion", {}),
        intervention_plan=result.get("intervention_plan", {}),
        privacy_note="Stored derived evidence only (quotes + constitution excerpts). No raw audio/video."
    )
    ledger_48h.insert(0, entry)

    # Vibe
    notify = bool(result.get("intervention_plan", {}).get("should_notify", False))
    vibe_history.append(VibePoint(ts_utc=ts, level=tension_level, notify=notify))

    # Tier 1 (events)
    tier1_events_48h.insert(0, Tier1Record(ts_utc=ts, events=events))

    # Tier 2 (summary)
    con = result.get("conclusion", {})
    plan = result.get("intervention_plan", {})
    summary_text = (
        f"{con.get('type','unknown')}: {con.get('one_sentence_summary','')}"
        f" | notify={plan.get('should_notify', False)} via {plan.get('channel','none')}"
    )
    t2 = Tier2Summary(
        ts_utc=ts,
        summary=summary_text,
        conclusion_type=con.get("type", "unknown")
    )
    tier2_summaries_30d.insert(0, t2)

    # Tier 3 (fake embedding id)
    payload = json.dumps(asdict(t2), ensure_ascii=False)
    tier3_embeddings.insert(
        0,
        Tier3Embedding(
            ts_utc=ts,
            embedding_id=make_fake_embedding_id(payload),
            theme=t2.conclusion_type
        )
    )


def apply_retention_policy(
    *,
    ledger_48h: List[LedgerEntry],
    vibe_history: List[VibePoint],
    tier1_events_48h: List[Tier1Record],
    tier2_summaries_30d: List[Tier2Summary],
    tier3_embeddings: List[Tier3Embedding],
) -> None:
    # 48h for ledger + tier1
    ledger_48h[:] = prune_by_hours(ledger_48h, hours=48, keep_max=200)
    tier1_events_48h[:] = prune_by_hours(tier1_events_48h, hours=48, keep_max=200)

    # 30d for vibe + tier2
    vibe_history[:] = prune_by_days(vibe_history, days=30, keep_max=2000)
    tier2_summaries_30d[:] = prune_by_days(tier2_summaries_30d, days=30, keep_max=500)

    # Tier3 long-term: cap
    if len(tier3_embeddings) > 2000:
        del tier3_embeddings[2000:]


def export_payload(
    *,
    ledger_48h: List[LedgerEntry],
    vibe_history: List[VibePoint],
    tier2_summaries_30d: List[Tier2Summary],
    tier3_embeddings: List[Tier3Embedding],
) -> Dict[str, Any]:
    from dataclasses import asdict
    return {
        "ledger_48h": [asdict(e) for e in ledger_48h],
        "vibe_history_30d": [asdict(v) for v in vibe_history],
        "tier2_summaries_30d": [asdict(s) for s in tier2_summaries_30d],
        "tier3_embeddings": [asdict(e) for e in tier3_embeddings],
        "privacy_statement": (
            "This demo stores derived events and receipts. "
            "It does not store raw audio/video or face identity."
        ),
    }
