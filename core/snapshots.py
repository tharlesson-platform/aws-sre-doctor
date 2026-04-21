from __future__ import annotations

from copy import deepcopy


BASELINE_TEMPLATE = {
    "environment": "prod",
    "workload": {
        "type": "ecs",
        "name": "payments-api",
        "cluster": "prod-apps",
    },
    "metadata": {
        "collection_mode": "snapshot-template",
    },
    "ecs": {
        "service_desired_count": 0,
        "service_running_count": 0,
        "deployments_in_progress": 0,
        "task_failures": [],
        "secrets_pull_errors": [],
    },
    "ec2": {
        "instances": [],
    },
    "eks": {
        "cluster_name": "",
        "status": "",
        "version": "",
        "nodegroups": [],
        "addons": [],
    },
    "rds": {
        "instances": [],
    },
    "alb": {
        "load_balancers": [],
        "listeners": [],
        "target_groups": [],
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
        "file_systems": [],
    },
    "network": {
        "route_mismatch": False,
        "sg_mismatch": False,
        "nacl_mismatch": False,
        "dns_private_resolution": "ok",
        "observed_subnets": [],
        "observed_security_groups": [],
        "observed_vpc_ids": [],
    },
    "iam": {
        "task_execution_role": "ok",
        "task_role": "ok",
        "irsa": "ok",
        "roles": [],
    },
    "quotas": [],
}


HEALTHY_BASELINE = {
    "workload": {
        "type": "ecs",
        "name": "payments-api",
        "cluster": "prod-apps",
    },
    "ecs": {
        "service_desired_count": 2,
        "service_running_count": 2,
        "deployments_in_progress": 0,
    },
    "alb": {
        "load_balancers": [
            {
                "name": "payments-alb",
                "type": "application",
                "state": "active",
                "scheme": "internet-facing",
            }
        ],
        "target_groups": [
            {
                "name": "payments-api-tg",
                "healthy_targets": 2,
                "unhealthy_targets": 0,
                "health_check_path": "/healthz",
            }
        ],
    },
}


ECS_DEGRADED = {
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
        "load_balancers": [
            {
                "name": "payments-alb",
                "type": "application",
                "state": "active",
                "scheme": "internet-facing",
            }
        ],
        "target_groups": [
            {
                "name": "payments-api-tg",
                "healthy_targets": 1,
                "unhealthy_targets": 3,
                "health_check_path": "/healthz",
            }
        ],
    },
    "dependencies": {
        "ecr": "timeout",
        "secrets_manager": "access_denied",
    },
    "efs": {
        "mount_error": "mount.nfs4: Connection timed out",
    },
    "network": {
        "route_mismatch": True,
        "sg_mismatch": True,
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


EC2_DEGRADED = {
    "workload": {
        "type": "ec2",
        "name": "payments-ec2-fleet",
        "cluster": "",
    },
    "ec2": {
        "instances": [
            {
                "instance_id": "i-0payments001",
                "state": "running",
                "instance_type": "t3.large",
                "instance_status": "impaired",
                "system_status": "ok",
                "cpu_utilization": 92,
                "subnet_id": "subnet-ec201",
                "vpc_id": "vpc-prod001",
                "security_groups": ["sg-ec2app"],
            }
        ],
    },
    "network": {
        "sg_mismatch": True,
        "observed_subnets": ["subnet-ec201"],
        "observed_security_groups": ["sg-ec2app"],
        "observed_vpc_ids": ["vpc-prod001"],
    },
    "iam": {
        "roles": [
            {
                "name": "payments-ec2-role",
                "status": "review_required",
                "findings": ["missing_ssm_permissions"],
            }
        ],
    },
}


EKS_DEGRADED = {
    "workload": {
        "type": "eks",
        "name": "payments-cluster",
        "cluster": "payments-eks-prod",
    },
    "eks": {
        "cluster_name": "payments-eks-prod",
        "status": "ACTIVE",
        "version": "1.29",
        "health_issues": [],
        "nodegroups": [
            {
                "name": "payments-ng-a",
                "status": "DEGRADED",
                "desired_size": 4,
                "min_size": 2,
                "max_size": 6,
                "issues": [{"code": "AutoScalingGroupInstanceRefreshActive"}],
            }
        ],
        "addons": [
            {
                "name": "vpc-cni",
                "status": "DEGRADED",
                "version": "v1.18.3-eksbuild.1",
                "issues": [{"code": "InsufficientNumberOfReplicas"}],
            }
        ],
    },
    "network": {
        "dns_private_resolution": "fail",
        "observed_subnets": ["subnet-eks-a", "subnet-eks-b"],
        "observed_security_groups": ["sg-eks-cluster"],
        "observed_vpc_ids": ["vpc-prod001"],
    },
    "iam": {
        "irsa": "missing_oidc_provider",
    },
}


RDS_DEGRADED = {
    "workload": {
        "type": "rds",
        "name": "payments-db",
        "cluster": "",
    },
    "rds": {
        "instances": [
            {
                "db_instance_identifier": "payments-prod-db",
                "status": "modifying",
                "engine": "postgres",
                "multi_az": True,
                "publicly_accessible": False,
                "storage_encrypted": True,
                "allocated_storage_gb": 500,
                "storage_utilization": 0.91,
                "pending_modified_values": {"DBInstanceClass": "db.r6g.2xlarge"},
            }
        ],
    },
    "dependencies": {
        "cloudwatch": "ok",
    },
}


LB_TARGET_GROUP_DEGRADED = {
    "workload": {
        "type": "service",
        "name": "payments-edge",
        "cluster": "",
    },
    "alb": {
        "load_balancers": [
            {
                "name": "payments-edge-alb",
                "type": "application",
                "state": "provisioning",
                "scheme": "internet-facing",
            }
        ],
        "listeners": [
            {
                "protocol": "HTTPS",
                "port": 443,
            }
        ],
        "target_groups": [
            {
                "name": "payments-edge-tg",
                "healthy_targets": 0,
                "unhealthy_targets": 4,
                "health_check_path": "/readyz",
            }
        ],
    },
    "network": {
        "sg_mismatch": True,
    },
}


IAM_DEGRADED = {
    "workload": {
        "type": "service",
        "name": "payments-iam-path",
        "cluster": "",
    },
    "iam": {
        "task_execution_role": "missing_ecr_permissions",
        "task_role": "missing_secrets_manager_permissions",
        "irsa": "sts_assume_role_denied",
        "roles": [
            {
                "name": "payments-task-execution-role",
                "status": "review_required",
                "findings": ["missing_ecs_execution_policy"],
                "attached_policies": ["CloudWatchLogsFullAccess"],
                "trust_principals": ["ecs-tasks.amazonaws.com"],
            },
            {
                "name": "payments-irsa-role",
                "status": "review_required",
                "findings": ["missing_oidc_trust"],
                "attached_policies": ["AmazonS3ReadOnlyAccess"],
                "trust_principals": ["ec2.amazonaws.com"],
            },
        ],
    },
    "dependencies": {
        "secrets_manager": "access_denied",
        "sts": "access_denied",
    },
}


MULTI_SERVICE_DEGRADED = {
    "workload": {
        "type": "service",
        "name": "payments-platform",
        "cluster": "prod-apps",
    },
    "ecs": ECS_DEGRADED["ecs"],
    "alb": LB_TARGET_GROUP_DEGRADED["alb"],
    "rds": RDS_DEGRADED["rds"],
    "iam": IAM_DEGRADED["iam"],
    "dependencies": {
        "sts": "ok",
        "ecr": "timeout",
        "secrets_manager": "access_denied",
        "ssm": "ok",
        "cloudwatch": "ok",
    },
    "network": {
        "route_mismatch": True,
        "sg_mismatch": True,
        "nacl_mismatch": False,
        "dns_private_resolution": "fail",
    },
    "quotas": [
        {
            "name": "Application Load Balancers per Region",
            "utilization": 0.9,
            "limit": 50,
        },
        {
            "name": "RDS Storage",
            "utilization": 0.88,
            "limit": 1000,
        },
    ],
}


SCENARIOS = {
    "healthy-baseline": {"workload_type": "ecs", "snapshot": HEALTHY_BASELINE},
    "ecs-degraded": {"workload_type": "ecs", "snapshot": ECS_DEGRADED},
    "ec2-degraded": {"workload_type": "ec2", "snapshot": EC2_DEGRADED},
    "eks-degraded": {"workload_type": "eks", "snapshot": EKS_DEGRADED},
    "rds-degraded": {"workload_type": "rds", "snapshot": RDS_DEGRADED},
    "lb-target-group-degraded": {"workload_type": "service", "snapshot": LB_TARGET_GROUP_DEGRADED},
    "iam-degraded": {"workload_type": "service", "snapshot": IAM_DEGRADED},
    "multi-service-degraded": {"workload_type": "service", "snapshot": MULTI_SERVICE_DEGRADED},
}


def _deep_merge(base: dict, overlay: dict) -> dict:
    merged = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def build_snapshot_template(
    *,
    environment: str,
    workload_type: str,
    workload_name: str,
    cluster: str,
    scenario: str,
) -> dict:
    try:
        scenario_definition = SCENARIOS[scenario]
    except KeyError as exc:
        available = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"Unsupported scenario '{scenario}'. Available: {available}") from exc

    snapshot = _deep_merge(BASELINE_TEMPLATE, scenario_definition["snapshot"])
    resolved_workload_type = scenario_definition["workload_type"] if workload_type in {"", "auto"} else workload_type
    snapshot["environment"] = environment
    snapshot["workload"]["type"] = resolved_workload_type
    snapshot["workload"]["name"] = workload_name
    snapshot["workload"]["cluster"] = cluster if cluster else snapshot["workload"].get("cluster", "")

    target_groups = snapshot.get("alb", {}).get("target_groups", [])
    for target_group in target_groups:
        if not target_group.get("name") or target_group.get("name", "").endswith("-tg"):
            target_group["name"] = f"{workload_name}-tg"

    load_balancers = snapshot.get("alb", {}).get("load_balancers", [])
    for load_balancer in load_balancers:
        if not load_balancer.get("name"):
            load_balancer["name"] = f"{workload_name}-lb"

    if resolved_workload_type == "eks":
        snapshot["eks"]["cluster_name"] = cluster or workload_name
    return snapshot
