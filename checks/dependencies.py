from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, config: dict) -> list[dict]:
    dependency_failures = {
        name: status
        for name, status in snapshot.get("dependencies", {}).items()
        if status not in config.get("dependency_ok_values", ["ok", "healthy"])
    }
    if not dependency_failures:
        return []
    return [
        build_issue(
            title="Falha de reachability para APIs AWS",
            severity="high",
            impact="Dependências de controle da AWS estão degradadas",
            probable_causes=[
                "NAT/route quebrada",
                "DNS privado falhando",
                "NACL/SG bloqueando egress",
            ],
            next_steps=[
                "Testar STS/ECR/SSM/Secrets Manager a partir do workload",
                "Revisar rotas",
                "Conferir VPC endpoints quando existirem",
            ],
            evidence=dependency_failures,
            category="dependencies",
        )
    ]
