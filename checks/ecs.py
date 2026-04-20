from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, config: dict) -> list[dict]:
    issues: list[dict] = []
    ecs = snapshot.get("ecs", {})
    desired = int(ecs.get("service_desired_count", 0))
    running = int(ecs.get("service_running_count", 0))
    minimum_ratio = float(config.get("ecs_running_ratio_critical", 0.5))
    if desired and running < desired:
        ratio = running / desired if desired else 1
        severity = "critical" if ratio <= minimum_ratio else "high"
        issues.append(
            build_issue(
                title="ECS service unhealthy",
                severity=severity,
                impact=f"{desired - running} tasks indisponíveis",
                probable_causes=[
                    "Capacity shortage",
                    "Rolling deployment travado",
                    "Target group reprovando health checks",
                ],
                next_steps=[
                    "Validar eventos do service",
                    "Revisar task definition",
                    "Conferir target group, quotas e capacidade",
                ],
                evidence={"desired": desired, "running": running, "running_ratio": round(ratio, 2)},
                category="ecs",
            )
        )

    task_failures = ecs.get("task_failures", [])
    if task_failures:
        issues.append(
            build_issue(
                title="ECS task start failure",
                severity="high",
                impact="Novas tasks falham antes de estabilizar",
                probable_causes=[
                    "Imagem inacessível no ECR",
                    "ENI/IP insuficiente",
                    "Erro de bootstrap do container",
                ],
                next_steps=[
                    "Inspecionar stoppedReason",
                    "Checar subnet/ENI",
                    "Validar imagem, secret e IAM",
                ],
                evidence={"failures": task_failures},
                category="ecs",
            )
        )

    if ecs.get("secrets_pull_errors"):
        issues.append(
            build_issue(
                title="Falha ao puxar secrets",
                severity="high",
                impact="Containers podem iniciar sem configuração crítica",
                probable_causes=[
                    "Permission mismatch no Secrets Manager",
                    "Secret ausente",
                    "Network timeout para AWS API",
                ],
                next_steps=[
                    "Validar IAM role",
                    "Conferir nome/ARN do secret",
                    "Testar reachability da API",
                ],
                evidence={"secret_errors": ecs.get("secrets_pull_errors", [])},
                category="ecs",
            )
        )
    return issues
