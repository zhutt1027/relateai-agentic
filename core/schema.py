# Event Abstraction Layer
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class LedgerEntry:
    ts_utc: str
    fact_receipt: Dict[str, Any]
    conclusion: Dict[str, Any]
    intervention_plan: Dict[str, Any]
    privacy_note: str


@dataclass
class VibePoint:
    ts_utc: str
    level: str  # low|rising|high|unknown
    notify: bool


@dataclass
class Tier1Record:
    ts_utc: str
    events: Dict[str, Any]  # structured events only


@dataclass
class Tier2Summary:
    ts_utc: str
    summary: str
    conclusion_type: str


@dataclass
class Tier3Embedding:
    ts_utc: str
    embedding_id: str
    theme: str
