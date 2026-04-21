from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, _config: dict) -> list[dict]:
    eks = snapshot.get("eks", {})
    if not eks:
        return []

    issues: list[dict] = []
    status = eks.get("status")
    if status and status != "ACTIVE":
        issues.append(
            build_issue(
                title="EKS control plane unhealthy",
                severity="critical",
                impact="Cluster EKS não está ativo para operações de controle e scheduling",
                probable_causes=[
                    "Upgrade incompleto",
                    "Falha de control plane",
                    "Dependência de rede ou IAM do cluster degradada",
                ],
                next_steps=[
                    "Inspecionar estado do cluster no EKS",
                    "Revisar health issues do control plane",
                    "Validar role do cluster e VPC config",
                ],
                evidence={"cluster_status": status, "health_issues": eks.get("health_issues", [])},
                category="eks",
            )
        )

    unhealthy_nodegroups = [
        item for item in eks.get("nodegroups", []) if item.get("status") != "ACTIVE" or item.get("issues")
    ]
    if unhealthy_nodegroups:
        issues.append(
            build_issue(
                title="EKS node group degraded",
                severity="high",
                impact="Nós podem não estar disponíveis para workloads ou upgrades",
                probable_causes=[
                    "Node group em DEGRADED",
                    "Capacity shortage",
                    "AMI ou launch template inconsistente",
                ],
                next_steps=[
                    "Revisar node group status e health issues",
                    "Conferir autoscaling e capacidade por AZ",
                    "Validar AMI, SG e subnets do node group",
                ],
                evidence={"nodegroups": unhealthy_nodegroups},
                category="eks",
            )
        )

    degraded_addons = [item for item in eks.get("addons", []) if item.get("status") != "ACTIVE" or item.get("issues")]
    if degraded_addons:
        issues.append(
            build_issue(
                title="EKS addon degraded",
                severity="medium",
                impact="Addons essenciais podem comprometer rede, DNS ou observabilidade do cluster",
                probable_causes=[
                    "Addon incompatível com a versão do cluster",
                    "Upgrade de addon incompleto",
                    "Configuração ou permissão ausente",
                ],
                next_steps=[
                    "Revisar addon status e versão",
                    "Conferir health issues e compatibilidade",
                    "Planejar correção antes de novas mudanças no cluster",
                ],
                evidence={"addons": degraded_addons},
                category="eks",
                confidence="medium",
            )
        )

    return issues
