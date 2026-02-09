# Stage 2: fact receipt + intervention
from typing import Any, Dict


def summarize_for_tier2(result_json: Dict[str, Any]) -> str:
    con = result_json.get("conclusion", {})
    plan = result_json.get("intervention_plan", {})
    return (
        f"{con.get('type','unknown')}: {con.get('one_sentence_summary','')}"
        f" | notify={plan.get('should_notify', False)} via {plan.get('channel','none')}"
    )
