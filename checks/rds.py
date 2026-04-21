from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, config: dict) -> list[dict]:
    instances = snapshot.get("rds", {}).get("instances", [])
    if not instances:
        return []

    issues: list[dict] = []
    degraded = [instance for instance in instances if instance.get("status") not in {"available", "Available"}]
    if degraded:
        severity = "critical" if any(instance.get("status") in {"failed", "incompatible-parameters"} for instance in degraded) else "high"
        issues.append(
            build_issue(
                title="RDS instance degraded",
                severity=severity,
                impact="Banco pode estar indisponível ou instável para a aplicação",
                probable_causes=[
                    "Failover ou manutenção em andamento",
                    "Mudança pendente não aplicada corretamente",
                    "Problema de storage, parâmetro ou disponibilidade",
                ],
                next_steps=[
                    "Revisar DBInstanceStatus e eventos recentes",
                    "Conferir failover, pending modifications e alarmes",
                    "Validar conectividade da aplicação até o endpoint do banco",
                ],
                evidence={"instances": degraded},
                category="rds",
            )
        )

    hot_threshold = float(config.get("rds_storage_hot_threshold", 0.85))
    storage_hot = [
        instance
        for instance in instances
        if float(instance.get("storage_utilization") or 0.0) >= hot_threshold
    ]
    if storage_hot:
        issues.append(
            build_issue(
                title="RDS storage pressure",
                severity="medium",
                impact="Há risco de degradação por storage próximo do limite",
                probable_causes=[
                    "Crescimento de dados acima do esperado",
                    "Autogrowth ausente ou insuficiente",
                    "Retenção e housekeeping inadequados",
                ],
                next_steps=[
                    "Revisar FreeStorageSpace e autoscaling de storage",
                    "Comparar crescimento recente com retenção",
                    "Planejar expansão antes de nova janela crítica",
                ],
                evidence={"instances": storage_hot, "threshold": hot_threshold},
                category="rds",
                confidence="medium",
            )
        )

    return issues
