from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
import structlog
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
    ReadTimeoutError,
)


OK_STATUSES = {"ok", "healthy", "available", "active", "running"}


def _unique_strings(values: list[str] | tuple[str, ...] | None) -> list[str]:
    items = [value for value in values or [] if value]
    return list(dict.fromkeys(items))


class AWSLiveCollector:
    def __init__(
        self,
        *,
        region_name: str,
        profile: str | None = None,
        session: boto3.session.Session | None = None,
        clients: dict[str, Any] | None = None,
    ) -> None:
        self.session = session or boto3.session.Session(profile_name=profile, region_name=region_name)
        self.region_name = region_name or self.session.region_name or "us-east-1"
        self.clients = clients or {}
        self.logger = structlog.get_logger().bind(component="aws_live_collector", region=self.region_name)

    def client(self, service_name: str):
        if service_name not in self.clients:
            self.clients[service_name] = self.session.client(service_name, region_name=self.region_name)
        return self.clients[service_name]

    def collect_snapshot(
        self,
        *,
        environment: str,
        workload_type: str,
        workload_name: str,
        cluster: str | None = None,
        ecs_service: str | None = None,
        eks_cluster_name: str | None = None,
        ec2_instance_ids: list[str] | None = None,
        rds_instance_ids: list[str] | None = None,
        load_balancer_arns: list[str] | None = None,
        target_group_arns: list[str] | None = None,
        iam_role_arns: list[str] | None = None,
        efs_file_system_ids: list[str] | None = None,
        collect_dependencies: bool = True,
        collect_quotas: bool = True,
    ) -> dict:
        snapshot = {
            "environment": environment,
            "workload": {
                "type": workload_type,
                "name": workload_name,
                "cluster": cluster or eks_cluster_name or "",
            },
            "metadata": {
                "collection_mode": "boto3-live",
                "generated_at": datetime.now(tz=UTC).isoformat(),
                "region": self.region_name,
                "resource_targets": {
                    "ecs_service": ecs_service or "",
                    "eks_cluster_name": eks_cluster_name or "",
                    "ec2_instance_ids": _unique_strings(ec2_instance_ids),
                    "rds_instance_ids": _unique_strings(rds_instance_ids),
                    "load_balancer_arns": _unique_strings(load_balancer_arns),
                    "target_group_arns": _unique_strings(target_group_arns),
                    "iam_role_arns": _unique_strings(iam_role_arns),
                    "efs_file_system_ids": _unique_strings(efs_file_system_ids),
                },
                "discovered_target_group_arns": [],
                "discovered_load_balancer_arns": [],
                "discovered_iam_role_arns": [],
                "discovered_efs_file_system_ids": [],
                "dependency_details": {},
            },
            "ecs": {},
            "ec2": {"instances": []},
            "eks": {"nodegroups": [], "addons": []},
            "rds": {"instances": []},
            "alb": {"load_balancers": [], "listeners": [], "target_groups": []},
            "dependencies": {},
            "efs": {"mount_error": "", "file_systems": []},
            "network": {
                "route_mismatch": False,
                "sg_mismatch": False,
                "nacl_mismatch": False,
                "dns_private_resolution": "unknown",
                "observed_subnets": [],
                "observed_security_groups": [],
                "observed_vpc_ids": [],
            },
            "iam": {
                "task_execution_role": "",
                "irsa": "",
                "roles": [],
            },
            "quotas": [],
        }

        if collect_dependencies:
            self.collect_dependencies(snapshot)

        if ecs_service or (workload_type == "ecs" and cluster):
            self.collect_ecs_service(snapshot, cluster or "", ecs_service or workload_name)

        if ec2_instance_ids:
            self.collect_ec2_instances(snapshot, _unique_strings(ec2_instance_ids))

        if eks_cluster_name or workload_type == "eks":
            self.collect_eks_cluster(snapshot, eks_cluster_name or cluster or workload_name)

        if rds_instance_ids:
            self.collect_rds_instances(snapshot, _unique_strings(rds_instance_ids))

        discovered_lbs = _unique_strings(
            list(load_balancer_arns or []) + snapshot["metadata"]["discovered_load_balancer_arns"]
        )
        if discovered_lbs:
            self.collect_load_balancers(snapshot, discovered_lbs)

        discovered_tgs = _unique_strings(
            list(target_group_arns or []) + snapshot["metadata"]["discovered_target_group_arns"]
        )
        if discovered_tgs:
            self.collect_target_groups(snapshot, discovered_tgs)

        discovered_roles = _unique_strings(
            list(iam_role_arns or []) + snapshot["metadata"]["discovered_iam_role_arns"]
        )
        if discovered_roles:
            self.collect_iam_roles(snapshot, discovered_roles)

        discovered_efs = _unique_strings(
            list(efs_file_system_ids or []) + snapshot["metadata"]["discovered_efs_file_system_ids"]
        )
        if discovered_efs:
            self.collect_efs(snapshot, discovered_efs)

        if collect_quotas:
            self.collect_quotas(snapshot)

        return snapshot

    def collect_dependencies(self, snapshot: dict) -> None:
        sts_status, sts_response, sts_detail = self._safe_call("sts", "get_caller_identity")
        snapshot["dependencies"]["sts"] = sts_status
        if sts_detail:
            snapshot["metadata"]["dependency_details"]["sts"] = sts_detail
        if sts_response and "Account" in sts_response:
            snapshot["metadata"]["account_id"] = sts_response["Account"]

        dependency_calls = {
            "ecr": ("ecr", "describe_registry", {}),
            "secrets_manager": ("secretsmanager", "list_secrets", {"MaxResults": 1}),
            "ssm": ("ssm", "describe_parameters", {"MaxResults": 1}),
            "cloudwatch": ("cloudwatch", "describe_alarms", {"MaxRecords": 1}),
        }
        for logical_name, (service_name, operation, kwargs) in dependency_calls.items():
            status, _, detail = self._safe_call(service_name, operation, **kwargs)
            snapshot["dependencies"][logical_name] = status
            if detail:
                snapshot["metadata"]["dependency_details"][logical_name] = detail

    def collect_ecs_service(self, snapshot: dict, cluster: str, service_name: str) -> None:
        status, response, detail = self._safe_call("ecs", "describe_services", cluster=cluster, services=[service_name])
        if status != "ok" or not response or not response.get("services"):
            snapshot["ecs"] = {
                "service_desired_count": 0,
                "service_running_count": 0,
                "deployments_in_progress": 0,
                "task_failures": [detail or f"Service {service_name} not found"],
                "secrets_pull_errors": [],
                "service_status": "unavailable",
            }
            return

        service = response["services"][0]
        task_failures = [event["message"] for event in service.get("events", [])[:5]]
        stopped_task_arns: list[str] = []
        list_status, list_response, _ = self._safe_call(
            "ecs",
            "list_tasks",
            cluster=cluster,
            serviceName=service_name,
            desiredStatus="STOPPED",
            maxResults=10,
        )
        if list_status == "ok" and list_response:
            stopped_task_arns = list_response.get("taskArns", [])

        if stopped_task_arns:
            describe_status, tasks_response, task_detail = self._safe_call(
                "ecs",
                "describe_tasks",
                cluster=cluster,
                tasks=stopped_task_arns,
            )
            if describe_status == "ok" and tasks_response:
                for task in tasks_response.get("tasks", []):
                    if task.get("stoppedReason"):
                        task_failures.append(task["stoppedReason"])
                    for container in task.get("containers", []):
                        if container.get("reason"):
                            task_failures.append(container["reason"])
            elif task_detail:
                task_failures.append(task_detail)

        secrets_errors = [
            reason
            for reason in task_failures
            if any(keyword in reason.lower() for keyword in ["secret", "secretsmanager", "ssm", "accessdenied"])
        ]

        snapshot["ecs"] = {
            "service_desired_count": int(service.get("desiredCount", 0)),
            "service_running_count": int(service.get("runningCount", 0)),
            "deployments_in_progress": len(
                [item for item in service.get("deployments", []) if item.get("rolloutState") != "COMPLETED"]
            ),
            "task_failures": _unique_strings(task_failures),
            "secrets_pull_errors": _unique_strings(secrets_errors),
            "service_status": service.get("status", "UNKNOWN"),
        }

        awsvpc = service.get("networkConfiguration", {}).get("awsvpcConfiguration", {})
        self._extend_network_details(
            snapshot,
            subnets=awsvpc.get("subnets"),
            security_groups=awsvpc.get("securityGroups"),
        )

        discovered_tgs = [item.get("targetGroupArn") for item in service.get("loadBalancers", []) if item.get("targetGroupArn")]
        snapshot["metadata"]["discovered_target_group_arns"] = _unique_strings(
            snapshot["metadata"]["discovered_target_group_arns"] + discovered_tgs
        )

        task_definition_arn = service.get("taskDefinition")
        if not task_definition_arn:
            return

        task_def_status, task_def_response, task_def_detail = self._safe_call(
            "ecs",
            "describe_task_definition",
            taskDefinition=task_definition_arn,
            include=["TAGS"],
        )
        if task_def_status != "ok" or not task_def_response:
            snapshot["ecs"]["task_failures"] = _unique_strings(snapshot["ecs"]["task_failures"] + [task_def_detail or "task definition unavailable"])
            return

        task_definition = task_def_response.get("taskDefinition", {})
        execution_role_arn = task_definition.get("executionRoleArn", "")
        task_role_arn = task_definition.get("taskRoleArn", "")
        snapshot["iam"]["task_execution_role"] = "ok" if execution_role_arn else "missing"
        if task_role_arn and not snapshot["iam"].get("task_role"):
            snapshot["iam"]["task_role"] = "ok"
        discovered_roles = [role for role in [execution_role_arn, task_role_arn] if role]
        snapshot["metadata"]["discovered_iam_role_arns"] = _unique_strings(
            snapshot["metadata"]["discovered_iam_role_arns"] + discovered_roles
        )

        file_system_ids = []
        for volume in task_definition.get("volumes", []):
            efs_config = volume.get("efsVolumeConfiguration", {})
            if efs_config.get("fileSystemId"):
                file_system_ids.append(efs_config["fileSystemId"])
        snapshot["metadata"]["discovered_efs_file_system_ids"] = _unique_strings(
            snapshot["metadata"]["discovered_efs_file_system_ids"] + file_system_ids
        )

    def collect_ec2_instances(self, snapshot: dict, instance_ids: list[str]) -> None:
        status, response, detail = self._safe_call("ec2", "describe_instances", InstanceIds=instance_ids)
        if status != "ok" or not response:
            snapshot["ec2"]["instances"] = [{"instance_id": instance_id, "status": detail or "unavailable"} for instance_id in instance_ids]
            return

        status_map: dict[str, dict[str, str]] = {}
        instance_status_call, instance_status_response, _ = self._safe_call(
            "ec2",
            "describe_instance_status",
            InstanceIds=instance_ids,
            IncludeAllInstances=True,
        )
        if instance_status_call == "ok" and instance_status_response:
            for item in instance_status_response.get("InstanceStatuses", []):
                status_map[item["InstanceId"]] = {
                    "instance_status": item.get("InstanceStatus", {}).get("Status", "unknown"),
                    "system_status": item.get("SystemStatus", {}).get("Status", "unknown"),
                }

        instances = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance["InstanceId"]
                instance_profile_arn = instance.get("IamInstanceProfile", {}).get("Arn", "")
                if instance_profile_arn:
                    role_arns = self._collect_instance_profile_roles(instance_profile_arn)
                    snapshot["metadata"]["discovered_iam_role_arns"] = _unique_strings(
                        snapshot["metadata"]["discovered_iam_role_arns"] + role_arns
                    )

                instances.append(
                    {
                        "instance_id": instance_id,
                        "state": instance.get("State", {}).get("Name", "unknown"),
                        "instance_type": instance.get("InstanceType", "unknown"),
                        "subnet_id": instance.get("SubnetId", ""),
                        "vpc_id": instance.get("VpcId", ""),
                        "security_groups": [group.get("GroupId", "") for group in instance.get("SecurityGroups", [])],
                        "iam_instance_profile_arn": instance_profile_arn,
                        "private_ip": instance.get("PrivateIpAddress", ""),
                        "instance_status": status_map.get(instance_id, {}).get("instance_status", "unknown"),
                        "system_status": status_map.get(instance_id, {}).get("system_status", "unknown"),
                    }
                )
                self._extend_network_details(
                    snapshot,
                    subnets=[instance.get("SubnetId", "")],
                    security_groups=[group.get("GroupId", "") for group in instance.get("SecurityGroups", [])],
                    vpc_ids=[instance.get("VpcId", "")],
                )
        snapshot["ec2"]["instances"] = instances

    def collect_eks_cluster(self, snapshot: dict, cluster_name: str) -> None:
        status, response, detail = self._safe_call("eks", "describe_cluster", name=cluster_name)
        if status != "ok" or not response:
            snapshot["eks"] = {"cluster_name": cluster_name, "status": detail or "unavailable", "nodegroups": [], "addons": []}
            return

        cluster = response.get("cluster", {})
        resources_vpc = cluster.get("resourcesVpcConfig", {})
        snapshot["eks"] = {
            "cluster_name": cluster_name,
            "status": cluster.get("status", "UNKNOWN"),
            "version": cluster.get("version", ""),
            "endpoint_public_access": resources_vpc.get("endpointPublicAccess", False),
            "health_issues": cluster.get("health", {}).get("issues", []),
            "nodegroups": [],
            "addons": [],
        }
        snapshot["iam"]["irsa"] = "ok" if cluster.get("identity", {}).get("oidc", {}).get("issuer") else "missing_oidc_provider"
        cluster_role = cluster.get("roleArn", "")
        if cluster_role:
            snapshot["metadata"]["discovered_iam_role_arns"] = _unique_strings(
                snapshot["metadata"]["discovered_iam_role_arns"] + [cluster_role]
            )
        self._extend_network_details(
            snapshot,
            subnets=resources_vpc.get("subnetIds"),
            security_groups=resources_vpc.get("securityGroupIds"),
            vpc_ids=[resources_vpc.get("vpcId", "")],
        )

        nodegroups_status, nodegroups_response, _ = self._safe_call("eks", "list_nodegroups", clusterName=cluster_name)
        if nodegroups_status == "ok" and nodegroups_response:
            for nodegroup_name in nodegroups_response.get("nodegroups", []):
                describe_status, nodegroup_response, _ = self._safe_call(
                    "eks",
                    "describe_nodegroup",
                    clusterName=cluster_name,
                    nodegroupName=nodegroup_name,
                )
                if describe_status != "ok" or not nodegroup_response:
                    continue
                nodegroup = nodegroup_response.get("nodegroup", {})
                snapshot["eks"]["nodegroups"].append(
                    {
                        "name": nodegroup_name,
                        "status": nodegroup.get("status", "UNKNOWN"),
                        "ami_type": nodegroup.get("amiType", ""),
                        "desired_size": nodegroup.get("scalingConfig", {}).get("desiredSize", 0),
                        "min_size": nodegroup.get("scalingConfig", {}).get("minSize", 0),
                        "max_size": nodegroup.get("scalingConfig", {}).get("maxSize", 0),
                        "issues": nodegroup.get("health", {}).get("issues", []),
                    }
                )

        addons_status, addons_response, _ = self._safe_call("eks", "list_addons", clusterName=cluster_name)
        if addons_status == "ok" and addons_response:
            for addon_name in addons_response.get("addons", []):
                describe_status, addon_response, _ = self._safe_call(
                    "eks",
                    "describe_addon",
                    clusterName=cluster_name,
                    addonName=addon_name,
                )
                if describe_status != "ok" or not addon_response:
                    continue
                addon = addon_response.get("addon", {})
                snapshot["eks"]["addons"].append(
                    {
                        "name": addon_name,
                        "status": addon.get("status", "UNKNOWN"),
                        "version": addon.get("addonVersion", ""),
                        "issues": addon.get("health", {}).get("issues", []),
                    }
                )

    def collect_rds_instances(self, snapshot: dict, instance_ids: list[str]) -> None:
        instances = []
        for instance_id in instance_ids:
            status, response, detail = self._safe_call("rds", "describe_db_instances", DBInstanceIdentifier=instance_id)
            if status != "ok" or not response or not response.get("DBInstances"):
                instances.append({"db_instance_identifier": instance_id, "status": detail or "unavailable"})
                continue

            db_instance = response["DBInstances"][0]
            allocated_storage = float(db_instance.get("AllocatedStorage", 0))
            free_storage_space = self._fetch_cloudwatch_metric(
                namespace="AWS/RDS",
                metric_name="FreeStorageSpace",
                dimensions=[{"Name": "DBInstanceIdentifier", "Value": instance_id}],
                statistic="Minimum",
                period=300,
            )
            storage_utilization = None
            if allocated_storage and free_storage_space is not None:
                total_bytes = allocated_storage * 1024 * 1024 * 1024
                storage_utilization = round(max(0.0, 1 - (free_storage_space / total_bytes)), 2)

            instances.append(
                {
                    "db_instance_identifier": instance_id,
                    "status": db_instance.get("DBInstanceStatus", "unknown"),
                    "engine": db_instance.get("Engine", ""),
                    "multi_az": db_instance.get("MultiAZ", False),
                    "publicly_accessible": db_instance.get("PubliclyAccessible", False),
                    "storage_encrypted": db_instance.get("StorageEncrypted", False),
                    "allocated_storage_gb": allocated_storage,
                    "storage_utilization": storage_utilization,
                    "pending_modified_values": db_instance.get("PendingModifiedValues", {}),
                }
            )

            subnet_ids = [item.get("SubnetIdentifier", "") for item in db_instance.get("DBSubnetGroup", {}).get("Subnets", [])]
            security_groups = [group.get("VpcSecurityGroupId", "") for group in db_instance.get("VpcSecurityGroups", [])]
            self._extend_network_details(
                snapshot,
                subnets=subnet_ids,
                security_groups=security_groups,
                vpc_ids=[db_instance.get("DBSubnetGroup", {}).get("VpcId", "")],
            )

        snapshot["rds"]["instances"] = instances

    def collect_load_balancers(self, snapshot: dict, load_balancer_arns: list[str]) -> None:
        status, response, detail = self._safe_call("elbv2", "describe_load_balancers", LoadBalancerArns=load_balancer_arns)
        if status != "ok" or not response:
            snapshot["alb"]["load_balancers"] = [{"arn": arn, "state": detail or "unavailable"} for arn in load_balancer_arns]
            return

        lbs = []
        discovered_target_groups: list[str] = []
        for load_balancer in response.get("LoadBalancers", []):
            lbs.append(
                {
                    "arn": load_balancer.get("LoadBalancerArn", ""),
                    "name": load_balancer.get("LoadBalancerName", ""),
                    "type": load_balancer.get("Type", ""),
                    "scheme": load_balancer.get("Scheme", ""),
                    "dns_name": load_balancer.get("DNSName", ""),
                    "state": load_balancer.get("State", {}).get("Code", "unknown"),
                }
            )
            self._extend_network_details(
                snapshot,
                subnets=[item.get("SubnetId", "") for item in load_balancer.get("AvailabilityZones", [])],
                security_groups=load_balancer.get("SecurityGroups", []),
                vpc_ids=[load_balancer.get("VpcId", "")],
            )

            listeners_status, listeners_response, _ = self._safe_call(
                "elbv2",
                "describe_listeners",
                LoadBalancerArn=load_balancer.get("LoadBalancerArn", ""),
            )
            if listeners_status != "ok" or not listeners_response:
                continue
            for listener in listeners_response.get("Listeners", []):
                snapshot["alb"]["listeners"].append(
                    {
                        "load_balancer_arn": load_balancer.get("LoadBalancerArn", ""),
                        "listener_arn": listener.get("ListenerArn", ""),
                        "port": listener.get("Port", 0),
                        "protocol": listener.get("Protocol", ""),
                        "default_actions": listener.get("DefaultActions", []),
                    }
                )
                discovered_target_groups.extend(
                    [action.get("TargetGroupArn", "") for action in listener.get("DefaultActions", []) if action.get("TargetGroupArn")]
                )
        snapshot["alb"]["load_balancers"] = lbs
        snapshot["metadata"]["discovered_target_group_arns"] = _unique_strings(
            snapshot["metadata"]["discovered_target_group_arns"] + discovered_target_groups
        )

    def collect_target_groups(self, snapshot: dict, target_group_arns: list[str]) -> None:
        status, response, detail = self._safe_call("elbv2", "describe_target_groups", TargetGroupArns=target_group_arns)
        if status != "ok" or not response:
            snapshot["alb"]["target_groups"] = [{"arn": arn, "status": detail or "unavailable"} for arn in target_group_arns]
            return

        target_groups = []
        discovered_lbs: list[str] = []
        for target_group in response.get("TargetGroups", []):
            health_status, health_response, health_detail = self._safe_call(
                "elbv2",
                "describe_target_health",
                TargetGroupArn=target_group.get("TargetGroupArn", ""),
            )
            descriptions = health_response.get("TargetHealthDescriptions", []) if health_status == "ok" and health_response else []
            healthy_targets = len([item for item in descriptions if item.get("TargetHealth", {}).get("State") == "healthy"])
            unhealthy_targets = len(
                [item for item in descriptions if item.get("TargetHealth", {}).get("State") not in {"healthy", "unused"}]
            )
            if health_detail:
                unhealthy_targets = max(unhealthy_targets, 1)
            target_groups.append(
                {
                    "arn": target_group.get("TargetGroupArn", ""),
                    "name": target_group.get("TargetGroupName", ""),
                    "target_type": target_group.get("TargetType", ""),
                    "healthy_targets": healthy_targets,
                    "unhealthy_targets": unhealthy_targets,
                    "registered_targets": len(descriptions),
                    "health_check_path": target_group.get("HealthCheckPath", ""),
                    "health_check_protocol": target_group.get("HealthCheckProtocol", ""),
                }
            )
            discovered_lbs.extend(target_group.get("LoadBalancerArns", []))
            self._extend_network_details(snapshot, vpc_ids=[target_group.get("VpcId", "")])
        snapshot["alb"]["target_groups"] = target_groups
        snapshot["metadata"]["discovered_load_balancer_arns"] = _unique_strings(
            snapshot["metadata"]["discovered_load_balancer_arns"] + discovered_lbs
        )

    def collect_iam_roles(self, snapshot: dict, role_arns: list[str]) -> None:
        roles = []
        for role_arn in role_arns:
            role_name = role_arn.split("/")[-1]
            status, response, detail = self._safe_call("iam", "get_role", RoleName=role_name)
            if status != "ok" or not response:
                roles.append({"arn": role_arn, "name": role_name, "status": detail or "unavailable", "findings": [detail or "role unavailable"]})
                if snapshot["iam"].get("task_execution_role") == "ok":
                    snapshot["iam"]["task_execution_role"] = detail or "access_denied"
                continue

            role = response.get("Role", {})
            attached_status, attached_response, _ = self._safe_call("iam", "list_attached_role_policies", RoleName=role_name)
            attached_policies = attached_response.get("AttachedPolicies", []) if attached_status == "ok" and attached_response else []
            findings = []
            if not attached_policies:
                findings.append("no_attached_policies")

            assume_statements = role.get("AssumeRolePolicyDocument", {}).get("Statement", [])
            trust_principals = []
            has_federated_principal = False
            for statement in assume_statements:
                principal = statement.get("Principal", {})
                if isinstance(principal, dict):
                    trust_principals.extend(str(value) for value in principal.values())
                    if principal.get("Federated"):
                        has_federated_principal = True

            if "execution" in role_name.lower():
                policy_names = [item.get("PolicyName", "") for item in attached_policies]
                if "AmazonECSTaskExecutionRolePolicy" not in policy_names:
                    findings.append("missing_ecs_execution_policy")
                    snapshot["iam"]["task_execution_role"] = "missing_ecr_permissions"

            if has_federated_principal and snapshot["iam"].get("irsa") == "ok":
                snapshot["iam"]["irsa"] = "ok"

            roles.append(
                {
                    "arn": role_arn,
                    "name": role_name,
                    "status": "ok" if not findings else "review_required",
                    "attached_policies": [item.get("PolicyName", "") for item in attached_policies],
                    "trust_principals": trust_principals,
                    "findings": findings,
                }
            )
        snapshot["iam"]["roles"] = roles

    def collect_efs(self, snapshot: dict, file_system_ids: list[str]) -> None:
        file_systems = []
        mount_errors = []
        for file_system_id in file_system_ids:
            status, response, detail = self._safe_call("efs", "describe_file_systems", FileSystemId=file_system_id)
            if status != "ok" or not response or not response.get("FileSystems"):
                mount_errors.append(detail or f"{file_system_id} unavailable")
                continue

            file_system = response["FileSystems"][0]
            targets_status, targets_response, targets_detail = self._safe_call(
                "efs",
                "describe_mount_targets",
                FileSystemId=file_system_id,
            )
            mount_targets = targets_response.get("MountTargets", []) if targets_status == "ok" and targets_response else []
            if targets_detail:
                mount_errors.append(targets_detail)
            if file_system.get("LifeCycleState", "").lower() != "available":
                mount_errors.append(f"{file_system_id} lifecycle={file_system.get('LifeCycleState', 'unknown')}")
            if not mount_targets:
                mount_errors.append(f"{file_system_id} has no mount targets")
            for mount_target in mount_targets:
                sg_status, sg_response, _ = self._safe_call(
                    "efs",
                    "describe_mount_target_security_groups",
                    MountTargetId=mount_target.get("MountTargetId", ""),
                )
                security_groups = sg_response.get("SecurityGroups", []) if sg_status == "ok" and sg_response else []
                self._extend_network_details(
                    snapshot,
                    subnets=[mount_target.get("SubnetId", "")],
                    security_groups=security_groups,
                    vpc_ids=[file_system.get("VpcId", "")],
                )

            file_systems.append(
                {
                    "file_system_id": file_system_id,
                    "life_cycle_state": file_system.get("LifeCycleState", "unknown"),
                    "encrypted": file_system.get("Encrypted", False),
                    "performance_mode": file_system.get("PerformanceMode", ""),
                    "mount_target_count": len(mount_targets),
                }
            )
        snapshot["efs"]["file_systems"] = file_systems
        snapshot["efs"]["mount_error"] = "; ".join(_unique_strings(mount_errors))

    def collect_quotas(self, snapshot: dict) -> None:
        snapshot["metadata"]["quota_collection"] = "not_collected_live"

    def _collect_instance_profile_roles(self, instance_profile_arn: str) -> list[str]:
        profile_name = instance_profile_arn.split("/")[-1]
        status, response, _ = self._safe_call("iam", "get_instance_profile", InstanceProfileName=profile_name)
        if status != "ok" or not response:
            return []
        roles = response.get("InstanceProfile", {}).get("Roles", [])
        return [role.get("Arn", "") for role in roles if role.get("Arn")]

    def _fetch_cloudwatch_metric(
        self,
        *,
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]],
        statistic: str,
        period: int,
    ) -> float | None:
        end_time = datetime.now(tz=UTC)
        start_time = end_time - timedelta(hours=1)
        status, response, _ = self._safe_call(
            "cloudwatch",
            "get_metric_statistics",
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[statistic],
        )
        if status != "ok" or not response:
            return None
        datapoints = response.get("Datapoints", [])
        if not datapoints:
            return None
        latest = sorted(datapoints, key=lambda item: item["Timestamp"])[-1]
        return float(latest.get(statistic, 0.0))

    def _extend_network_details(
        self,
        snapshot: dict,
        *,
        subnets: list[str] | None = None,
        security_groups: list[str] | None = None,
        vpc_ids: list[str] | None = None,
    ) -> None:
        network = snapshot["network"]
        network["observed_subnets"] = _unique_strings(network["observed_subnets"] + _unique_strings(subnets))
        network["observed_security_groups"] = _unique_strings(
            network["observed_security_groups"] + _unique_strings(security_groups)
        )
        network["observed_vpc_ids"] = _unique_strings(network["observed_vpc_ids"] + _unique_strings(vpc_ids))

    def _safe_call(self, service_name: str, operation_name: str, **kwargs) -> tuple[str, Any | None, str | None]:
        client = self.client(service_name)
        operation = getattr(client, operation_name)
        try:
            response = operation(**kwargs)
            self.logger.info("aws_call_ok", service=service_name, operation=operation_name)
            return "ok", response, None
        except (EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError) as exc:
            detail = exc.__class__.__name__
            self.logger.warning("aws_call_timeout", service=service_name, operation=operation_name, detail=detail)
            return "timeout", None, detail
        except (NoCredentialsError, PartialCredentialsError) as exc:
            detail = exc.__class__.__name__
            self.logger.warning("aws_call_credentials_error", service=service_name, operation=operation_name, detail=detail)
            return "credentials_error", None, detail
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "ClientError")
            status = "access_denied" if any(tag in code.lower() for tag in ["accessdenied", "unauthorized"]) else "error"
            self.logger.warning("aws_call_client_error", service=service_name, operation=operation_name, code=code)
            return status, None, code
        except BotoCoreError as exc:
            detail = exc.__class__.__name__
            self.logger.warning("aws_call_error", service=service_name, operation=operation_name, detail=detail)
            return "error", None, detail
