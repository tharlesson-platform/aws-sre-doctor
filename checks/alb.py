from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, _config: dict) -> list[dict]:
    target_groups = [
        tg
        for tg in snapshot.get("alb", {}).get("target_groups", [])
        if int(tg.get("unhealthy_targets", 0)) > 0
    ]
    listeners = snapshot.get("alb", {}).get("listeners", [])
    issues: list[dict] = []
    if target_groups:
        issues.append(
            build_issue(
                title="ALB target unhealthy",
                severity="high",
                impact="Tráfego pode estar sendo derrubado ou concentrado em poucos targets",
                probable_causes=[
                    "Health check path incorreto",
                    "App devolvendo 5xx",
                    "Security group bloqueando ALB -> target",
                ],
                next_steps=[
                    "Validar path de health check",
                    "Conferir security groups",
                    "Revisar logs de aplicação",
                ],
                evidence={"target_groups": target_groups, "listeners": listeners},
                category="alb",
            )
        )
    return issues
