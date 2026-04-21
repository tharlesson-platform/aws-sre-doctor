from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, _config: dict) -> list[dict]:
    issues: list[dict] = []
    mount_error = snapshot.get("efs", {}).get("mount_error")
    if mount_error:
        issues.append(
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
        )
    degraded_file_systems = [
        fs
        for fs in snapshot.get("efs", {}).get("file_systems", [])
        if fs.get("life_cycle_state", "").lower() != "available" or int(fs.get("mount_target_count", 0)) == 0
    ]
    if degraded_file_systems:
        issues.append(
            build_issue(
                title="EFS filesystem not ready",
                severity="high",
                impact="Filesystem EFS não está pronto para atender mounts nas AZs esperadas",
                probable_causes=[
                    "Lifecycle state diferente de available",
                    "Mount targets ausentes",
                    "Provisionamento incompleto",
                ],
                next_steps=[
                    "Validar lifecycle state do filesystem",
                    "Conferir mount targets por AZ",
                    "Revisar security groups das mount targets",
                ],
                evidence={"file_systems": degraded_file_systems},
                category="efs",
            )
        )
    return issues
