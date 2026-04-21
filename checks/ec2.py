from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, config: dict) -> list[dict]:
    instances = snapshot.get("ec2", {}).get("instances", [])
    if not instances:
        return []

    issues: list[dict] = []
    unhealthy = [
        instance
        for instance in instances
        if instance.get("state") != "running"
        or instance.get("instance_status") not in {"ok", "not-applicable", "unknown"}
        or instance.get("system_status") not in {"ok", "not-applicable", "unknown"}
    ]
    if unhealthy:
        severity = "critical" if any(instance.get("state") != "running" for instance in unhealthy) else "high"
        issues.append(
            build_issue(
                title="EC2 instance health issue",
                severity=severity,
                impact="Instâncias EC2 relevantes estão fora do estado saudável esperado",
                probable_causes=[
                    "Status check falhando",
                    "Problema de rede ou host subjacente",
                    "Instância em reboot, stop ou degradação operacional",
                ],
                next_steps=[
                    "Revisar system status e instance status",
                    "Conferir reachability e eventos da instância",
                    "Validar SG, NACL e volume raiz",
                ],
                evidence={"instances": unhealthy},
                category="ec2",
            )
        )

    cpu_threshold = float(config.get("ec2_cpu_hot_threshold", 85.0))
    cpu_hot = [
        instance
        for instance in instances
        if float(instance.get("cpu_utilization", 0.0) or 0.0) >= cpu_threshold
    ]
    if cpu_hot:
        issues.append(
            build_issue(
                title="EC2 CPU pressure",
                severity="medium",
                impact="Instâncias estão próximas de saturação de CPU",
                probable_causes=[
                    "Load spike",
                    "Rightsizing incorreto",
                    "Workload degradado ou em retry",
                ],
                next_steps=[
                    "Validar CPUUtilization e load average",
                    "Comparar com autoscaling e capacity planning",
                    "Revisar processos e threads em maior consumo",
                ],
                evidence={"instances": cpu_hot, "threshold": cpu_threshold},
                category="ec2",
                confidence="medium",
            )
        )

    return issues
