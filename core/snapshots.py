from __future__ import annotations

from copy import deepcopy


HEALTHY_BASELINE = {
    "environment": "prod",
    "workload": {
        "type": "ecs",
        "name": "payments-api",
        "cluster": "prod-apps",
    },
    "ecs": {
        "service_desired_count": 2,
        "service_running_count": 2,
        "deployments_in_progress": 0,
        "task_failures": [],
        "secrets_pull_errors": [],
    },
    "alb": {
        "target_groups": [
            {
                "name": "payments-api-tg",
                "healthy_targets": 2,
                "unhealthy_targets": 0,
                "health_check_path": "/healthz",
            }
        ]
    },
    "dependencies": {
        "sts": "ok",
        "ecr": "ok",
        "secrets_manager": "ok",
        "ssm": "ok",
        "cloudwatch": "ok",
    },
    "efs": {
        "mount_error": "",
    },
    "network": {
        "route_mismatch": False,
        "sg_mismatch": False,
        "nacl_mismatch": False,
        "dns_private_resolution": "ok",
    },
    "iam": {
        "task_execution_role": "ok",
        "irsa": "ok",
    },
    "quotas": [],
}


ECS_DEGRADED = {
    "environment": "prod",
    "workload": {
        "type": "ecs",
        "name": "payments-api",
        "cluster": "prod-apps",
    },
    "ecs": {
        "service_desired_count": 4,
        "service_running_count": 2,
        "deployments_in_progress": 1,
        "task_failures": [
            "RESOURCE:ENI",
            "CannotPullContainerError",
        ],
        "secrets_pull_errors": [
            "AccessDeniedException",
        ],
    },
    "alb": {
        "target_groups": [
            {
                "name": "payments-api-tg",
                "healthy_targets": 1,
                "unhealthy_targets": 3,
                "health_check_path": "/healthz",
            }
        ]
    },
    "dependencies": {
        "sts": "ok",
        "ecr": "timeout",
        "secrets_manager": "access_denied",
        "ssm": "ok",
        "cloudwatch": "ok",
    },
    "efs": {
        "mount_error": "mount.nfs4: Connection timed out",
    },
    "network": {
        "route_mismatch": True,
        "sg_mismatch": True,
        "nacl_mismatch": False,
        "dns_private_resolution": "fail",
    },
    "iam": {
        "task_execution_role": "missing_ecr_permissions",
        "irsa": "sts_assume_role_denied",
    },
    "quotas": [
        {
            "name": "Fargate vCPU",
            "utilization": 0.94,
            "limit": 100,
        }
    ],
}


SCENARIOS = {
    "healthy-baseline": HEALTHY_BASELINE,
    "ecs-degraded": ECS_DEGRADED,
}


def build_snapshot_template(
    *,
    environment: str,
    workload_type: str,
    workload_name: str,
    cluster: str,
    scenario: str,
) -> dict:
    try:
        snapshot = deepcopy(SCENARIOS[scenario])
    except KeyError as exc:
        available = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"Unsupported scenario '{scenario}'. Available: {available}") from exc

    snapshot["environment"] = environment
    snapshot["workload"]["type"] = workload_type
    snapshot["workload"]["name"] = workload_name
    snapshot["workload"]["cluster"] = cluster

    target_groups = snapshot.get("alb", {}).get("target_groups", [])
    for target_group in target_groups:
        target_group["name"] = f"{workload_name}-tg"

    return snapshot
