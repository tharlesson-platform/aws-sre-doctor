from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, _config: dict) -> list[dict]:
    iam = snapshot.get("iam", {})
    if not iam.get("task_execution_role") and not iam.get("irsa"):
        return []
    return [
        build_issue(
            title="IAM permission mismatch",
            severity="high",
            impact="Permissões atuais não atendem o caminho operacional do workload",
            probable_causes=[
                "Policy insuficiente",
                "Trust policy incorreta",
                "IRSA apontando para service account errada",
            ],
            next_steps=[
                "Revisar execution role e task role",
                "Checar trust relationship",
                "Comparar permissões com API falha",
            ],
            evidence=iam,
            category="iam",
        )
    ]
