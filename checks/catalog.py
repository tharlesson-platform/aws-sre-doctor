from __future__ import annotations

from checks import alb, dependencies, ec2, ecs, efs, eks, iam, network, quotas, rds
from core.engine import aggregate_report


CHECK_PIPELINE = [
    ecs.run,
    ec2.run,
    eks.run,
    rds.run,
    alb.run,
    dependencies.run,
    efs.run,
    network.run,
    iam.run,
    quotas.run,
]


def run_checks(snapshot: dict, config: dict) -> dict:
    issues: list[dict] = []
    for check in CHECK_PIPELINE:
        issues.extend(check(snapshot, config))
    return aggregate_report(snapshot, issues, config)
