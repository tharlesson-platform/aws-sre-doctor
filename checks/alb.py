from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, _config: dict) -> list[dict]:
    load_balancers = [
        lb
        for lb in snapshot.get("alb", {}).get("load_balancers", [])
        if lb.get("state", "").lower() not in {"active", "provisioned"}
    ]
    target_groups = [
        tg
        for tg in snapshot.get("alb", {}).get("target_groups", [])
        if int(tg.get("unhealthy_targets", 0)) > 0
    ]
    listeners = snapshot.get("alb", {}).get("listeners", [])
    issues: list[dict] = []
    if load_balancers:
        issues.append(
            build_issue(
                title="Load balancer not active",
                severity="high",
                impact="O balanceador pode não estar pronto para encaminhar tráfego corretamente",
                probable_causes=[
                    "Provisioning incompleto",
                    "Mudança recente em listener ou subnet",
                    "Erro de integração com target groups",
                ],
                next_steps=[
                    "Validar estado do load balancer",
                    "Conferir listeners e AZs associadas",
                    "Revisar target groups e mudanças recentes",
                ],
                evidence={"load_balancers": load_balancers},
                category="alb",
            )
        )
    if target_groups:
        severity = "critical" if any(int(tg.get("healthy_targets", 0)) == 0 for tg in target_groups) else "high"
        issues.append(
            build_issue(
                title="ALB target unhealthy",
                severity=severity,
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
