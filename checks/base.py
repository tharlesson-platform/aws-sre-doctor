from __future__ import annotations

from typing import Any


def build_issue(
    title: str,
    severity: str,
    impact: str,
    probable_causes: list[str],
    next_steps: list[str],
    evidence: dict[str, Any],
    category: str,
    confidence: str = "high",
) -> dict[str, Any]:
    return {
        "title": title,
        "severity": severity,
        "impact": impact,
        "probable_causes": probable_causes,
        "next_steps": next_steps,
        "evidence": evidence,
        "category": category,
        "confidence": confidence,
    }
