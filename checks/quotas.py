from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, config: dict) -> list[dict]:
    threshold = float(config.get("quota_hot_threshold", 0.9))
    hot_quotas = [quota for quota in snapshot.get("quotas", []) if float(quota.get("utilization", 0)) >= threshold]
    if not hot_quotas:
        return []
    severity = "high" if any(float(item.get("utilization", 0)) >= 0.97 for item in hot_quotas) else "medium"
    return [
        build_issue(
            title="Quotas relevantes em pressão",
            severity=severity,
            impact="Há risco de escala ou nova implantação falhar por limite",
            probable_causes=[
                "Fargate quota",
                "IPs/subnets próximos do limite",
                "Burst de incidentes concorrentes",
            ],
            next_steps=[
                "Abrir aumento de quota",
                "Revisar autoscaling",
                "Distribuir workloads por AZ/subnet",
            ],
            evidence={"quotas": hot_quotas, "threshold": threshold},
            category="quotas",
            confidence="medium",
        )
    ]
