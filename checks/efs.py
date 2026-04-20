from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, _config: dict) -> list[dict]:
    mount_error = snapshot.get("efs", {}).get("mount_error")
    if not mount_error:
        return []
    return [
        build_issue(
            title="EFS mount issue",
            severity="medium",
            impact="Workload pode falhar no startup por volume indisponível",
            probable_causes=[
                "Security group/NACL bloqueando 2049",
                "DNS da mount target falhando",
                "Mount targets ausentes na subnet",
            ],
            next_steps=[
                "Checar mount target por AZ",
                "Revisar TCP/2049",
                "Validar resolução DNS interna",
            ],
            evidence={"mount_error": mount_error},
            category="efs",
            confidence="medium",
        )
    ]
