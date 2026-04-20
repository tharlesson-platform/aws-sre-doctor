from __future__ import annotations

from checks import alb, dependencies, ecs, efs, iam, network, quotas
from core.engine import aggregate_report


CHECK_PIPELINE = [
    ecs.run,
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
    return aggregate_report(snapshot, issues)
