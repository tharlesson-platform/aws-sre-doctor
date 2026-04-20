from __future__ import annotations

from collections import OrderedDict


PENALTIES = {"low": 5, "medium": 10, "high": 18, "critical": 28}
SEVERITY_PRIORITY = ("critical", "high", "medium", "low")
IMPACT_BY_SEVERITY = {
    "critical": "customer-visible",
    "high": "service-degradation",
    "medium": "operational-risk",
    "low": "low-risk",
}


def aggregate_report(snapshot: dict, issues: list[dict]) -> dict:
    severity = "low"
    for value in SEVERITY_PRIORITY:
        if any(item["severity"] == value for item in issues):
            severity = value
            break

    health_score = max(0, 100 - sum(PENALTIES[item["severity"]] for item in issues))
    probable_causes = list(OrderedDict.fromkeys(cause for item in issues for cause in item["probable_causes"]))
    next_steps = list(OrderedDict.fromkeys(step for item in issues for step in item["next_steps"]))
    categories = list(OrderedDict.fromkeys(item["category"] for item in issues))

    summary = "Operação estável" if not issues else "Há indícios fortes de degradação operacional"
    if severity == "critical":
        summary = "Há falha crítica com potencial de impacto direto ao cliente"
    return {
        "title": "AWS SRE Doctor",
        "environment": snapshot.get("environment", "unknown"),
        "workload": snapshot.get("workload", {}),
        "health_score": health_score,
        "severity": severity,
        "impact_classification": IMPACT_BY_SEVERITY[severity],
        "summary": {
            "issues_found": len(issues),
            "diagnosis": summary,
            "categories": categories,
        },
        "issues": issues,
        "possible_causes": probable_causes,
        "suggested_next_steps": next_steps,
    }
