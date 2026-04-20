from checks.catalog import run_checks


def test_run_checks_builds_critical_report() -> None:
    snapshot = {
        "environment": "prod",
        "workload": {"name": "payments-api", "type": "ecs"},
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
    }
    config = {"quota_hot_threshold": 0.85, "ecs_running_ratio_critical": 0.5, "dependency_ok_values": ["ok", "healthy"]}
    report = run_checks(snapshot, config)
    assert report["severity"] == "critical"
    assert report["impact_classification"] == "customer-visible"
    assert report["health_score"] < 50
    assert any(item["category"] == "ecs" for item in report["issues"])
