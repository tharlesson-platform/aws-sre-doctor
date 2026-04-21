from checks.catalog import run_checks


def test_run_checks_builds_critical_report() -> None:
    snapshot = {
        "environment": "prod",
        "workload": {"name": "payments-api", "type": "ecs"},
        "metadata": {
            "generated_at": "2026-04-20T12:00:00+00:00",
            "alarm_events": [
                {
                    "name": "payments-api-5xx",
                    "state": "ALARM",
                    "timestamp": "2026-04-20T11:55:00+00:00",
                    "reason": "5xx above threshold",
                }
            ],
            "deploy_events": [
                {
                    "source": "ecs",
                    "type": "deployment",
                    "resource": "payments-api",
                    "status": "in_progress",
                    "timestamp": "2026-04-20T11:50:00+00:00",
                    "summary": "New task definition rollout in progress",
                }
            ],
            "network_assessment": {
                "route_findings": [{"summary": "Blackhole route found in rtb-123"}],
                "security_group_findings": [],
                "nacl_findings": [],
                "dns_findings": [],
            },
        },
        "ecs": {
            "service_desired_count": 4,
            "service_running_count": 1,
            "task_failures": ["CannotPullContainerError"],
            "secrets_pull_errors": ["AccessDenied"],
        },
        "alb": {"target_groups": [{"name": "payments-tg", "unhealthy_targets": 3, "healthy_targets": 1}]},
        "dependencies": {"sts": "ok", "ecr": "timeout", "secrets_manager": "access_denied"},
        "efs": {"mount_error": "timeout"},
        "network": {"route_mismatch": True, "sg_mismatch": False, "nacl_mismatch": False, "dns_private_resolution": "fail"},
        "iam": {"task_execution_role": "missing_ecr_permissions"},
        "quotas": [{"name": "Fargate vCPU", "utilization": 0.96}],
        "ec2": {
            "instances": [
                {
                    "instance_id": "i-1",
                    "state": "running",
                    "instance_status": "impaired",
                    "system_status": "ok",
                    "cpu_utilization": 91,
                }
            ]
        },
        "eks": {
            "cluster_name": "payments-eks-prod",
            "status": "ACTIVE",
            "nodegroups": [{"name": "payments-ng", "status": "DEGRADED", "issues": [{"code": "CapacityIssue"}]}],
            "addons": [],
        },
        "rds": {
            "instances": [
                {
                    "db_instance_identifier": "payments-db",
                    "status": "modifying",
                    "storage_utilization": 0.92,
                }
            ]
        },
    }
    config = {
        "quota_hot_threshold": 0.85,
        "ecs_running_ratio_critical": 0.5,
        "ec2_cpu_hot_threshold": 85,
        "rds_storage_hot_threshold": 0.85,
        "dependency_ok_values": ["ok", "healthy", "available", "active", "running"],
    }
    report = run_checks(snapshot, config)
    assert report["severity"] == "critical"
    assert report["impact_classification"] == "customer-visible"
    assert report["health_score"] < 50
    assert any(item["category"] == "ecs" for item in report["issues"])
    assert any(item["category"] == "ec2" for item in report["issues"])
    assert any(item["category"] == "eks" for item in report["issues"])
    assert any(item["category"] == "rds" for item in report["issues"])
    assert report["summary"]["correlated_signals"] >= 3
    assert any(item["title"] == "Deploy recente pode estar correlacionado com os alarmes" for item in report["correlations"]["correlated_hypotheses"])


def test_run_checks_keeps_healthy_snapshot_without_iam_false_positive() -> None:
    snapshot = {
        "environment": "prod",
        "workload": {"name": "payments-api", "type": "ecs"},
        "metadata": {
            "generated_at": "2026-04-20T12:00:00+00:00",
            "alarm_events": [],
            "deploy_events": [],
            "network_assessment": {
                "route_findings": [],
                "security_group_findings": [],
                "nacl_findings": [],
                "dns_findings": [],
            },
        },
        "ecs": {"service_desired_count": 2, "service_running_count": 2},
        "alb": {"target_groups": [{"name": "payments-tg", "unhealthy_targets": 0, "healthy_targets": 2}]},
        "dependencies": {"sts": "ok", "ecr": "ok", "secrets_manager": "ok", "ssm": "ok", "cloudwatch": "ok"},
        "efs": {"mount_error": ""},
        "network": {"route_mismatch": False, "sg_mismatch": False, "nacl_mismatch": False, "dns_private_resolution": "ok"},
        "iam": {"task_execution_role": "ok", "task_role": "ok", "irsa": "ok", "roles": []},
        "quotas": [],
        "ec2": {"instances": []},
        "eks": {"nodegroups": [], "addons": []},
        "rds": {"instances": []},
    }
    config = {
        "quota_hot_threshold": 0.85,
        "ecs_running_ratio_critical": 0.5,
        "dependency_ok_values": ["ok", "healthy", "available", "active", "running"],
    }
    report = run_checks(snapshot, config)
    assert report["issues"] == []
    assert report["severity"] == "low"
    assert report["summary"]["correlated_signals"] == 0
