# Stage 1: mock events 
import re
import json
from typing import Any, Dict, Optional, Tuple, List


def safe_parse_json(text: str) -> Optional[Dict[str, Any]]:
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


def parse_constitution_rules(constitution: str) -> List[str]:
    rules = []
    for line in constitution.splitlines():
        line = line.strip()
        if line.startswith("- "):
            rules.append(line[2:].strip())
    return rules


def extract_tension_level(events_dict: Dict[str, Any]) -> Tuple[str, bool]:
    level = "unknown"
    should_notify_hint = False
    for ev in events_dict.get("events", []):
        if ev.get("type") == "TensionSignalEvent":
            level = ev.get("level", "unknown")
            signals = ev.get("signals", [])
            should_notify_hint = level in ("rising", "high") or ("rapid_escalation" in signals)
            break
    return level, should_notify_hint
