from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, _config: dict) -> list[dict]:
    iam = snapshot.get("iam", {})
    issues: list[dict] = []
    role_findings = [role for role in iam.get("roles", []) if role.get("findings")]
    status_fields = {
        key: value
        for key, value in {
            "task_execution_role": iam.get("task_execution_role"),
            "task_role": iam.get("task_role"),
            "irsa": iam.get("irsa"),
        }.items()
        if value and value not in {"ok", "healthy", "attached"}
    }
    if status_fields or role_findings:
        issues.append(
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
                evidence={"status_fields": status_fields, "roles": role_findings},
                category="iam",
            )
        )
    return issues
