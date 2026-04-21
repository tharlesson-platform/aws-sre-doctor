from __future__ import annotations

from datetime import UTC, datetime

from botocore.exceptions import ClientError

from core.live_collectors import AWSLiveCollector


class FakeSTSClient:
    def get_caller_identity(self):
        return {"Account": "123456789012"}


class FakeECRClient:
    def describe_registry(self):
        return {"registryId": "123456789012"}


class FakeSecretsManagerClient:
    def list_secrets(self, MaxResults: int):
        raise ClientError({"Error": {"Code": "AccessDeniedException", "Message": "denied"}}, "ListSecrets")


class FakeSSMClient:
    def describe_parameters(self, MaxResults: int):
        return {"Parameters": []}


class FakeCloudWatchClient:
    def describe_alarms(self, MaxRecords: int, StateValue: str | None = None):
        if StateValue == "ALARM":
            return {
                "MetricAlarms": [
                    {
                        "AlarmName": "payments-api-5xx",
                        "AlarmDescription": "payments-api error rate high",
                        "StateValue": "ALARM",
                        "StateUpdatedTimestamp": datetime(2026, 4, 20, 11, 55, tzinfo=UTC),
                        "StateReason": "Threshold crossed",
                    }
                ]
            }
        return {"MetricAlarms": []}

    def get_metric_statistics(self, **kwargs):
        if kwargs["MetricName"] == "FreeStorageSpace":
            return {"Datapoints": [{"Timestamp": kwargs["EndTime"], "Minimum": 25 * 1024 * 1024 * 1024}]}
        return {"Datapoints": []}


class FakeECSClient:
    def describe_services(self, cluster: str, services: list[str]):
        return {
            "services": [
                {
                    "serviceName": services[0],
                    "desiredCount": 2,
                    "runningCount": 1,
                    "status": "ACTIVE",
                    "deployments": [
                        {
                            "id": "ecs-svc/123",
                            "rolloutState": "IN_PROGRESS",
                            "updatedAt": datetime(2026, 4, 20, 11, 52, tzinfo=UTC),
                            "rolloutStateReason": "Deployment started after task definition update",
                        }
                    ],
                    "events": [{"message": "service unable to reach steady state"}],
                    "loadBalancers": [
                        {"targetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/payments-api/abcdef"}
                    ],
                    "networkConfiguration": {
                        "awsvpcConfiguration": {
                            "subnets": ["subnet-a"],
                            "securityGroups": ["sg-a"],
                        }
                    },
                    "taskDefinition": "arn:aws:ecs:us-east-1:123456789012:task-definition/payments:12",
                }
            ]
        }

    def list_tasks(self, cluster: str, serviceName: str, desiredStatus: str, maxResults: int):
        return {"taskArns": ["arn:aws:ecs:task/payments-task-1"]}

    def describe_tasks(self, cluster: str, tasks: list[str]):
        return {
            "tasks": [
                {
                    "stoppedReason": "CannotPullContainerError: failed to resolve ref",
                    "containers": [{"reason": "AccessDeniedException retrieving secret"}],
                }
            ]
        }

    def describe_task_definition(self, taskDefinition: str, include: list[str]):
        return {
            "taskDefinition": {
                "executionRoleArn": "arn:aws:iam::123456789012:role/payments-task-execution-role",
                "taskRoleArn": "arn:aws:iam::123456789012:role/payments-task-role",
                "volumes": [{"efsVolumeConfiguration": {"fileSystemId": "fs-0123456789abcdef0"}}],
            }
        }


class FakeELBV2Client:
    def describe_target_groups(self, TargetGroupArns: list[str] | None = None):
        arns = TargetGroupArns or [
            "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/payments-api/abcdef"
        ]
        return {
            "TargetGroups": [
                {
                    "TargetGroupArn": arns[0],
                    "TargetGroupName": "payments-api-tg",
                    "TargetType": "ip",
                    "HealthCheckPath": "/healthz",
                    "HealthCheckProtocol": "HTTP",
                    "LoadBalancerArns": [
                        "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/payments-edge/123abc"
                    ],
                    "VpcId": "vpc-123",
                }
            ]
        }

    def describe_target_health(self, TargetGroupArn: str):
        return {
            "TargetHealthDescriptions": [
                {"TargetHealth": {"State": "healthy"}},
                {"TargetHealth": {"State": "unhealthy"}},
            ]
        }

    def describe_load_balancers(self, LoadBalancerArns: list[str] | None = None):
        arns = LoadBalancerArns or [
            "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/payments-edge/123abc"
        ]
        return {
            "LoadBalancers": [
                {
                    "LoadBalancerArn": arns[0],
                    "LoadBalancerName": "payments-edge",
                    "Type": "application",
                    "Scheme": "internet-facing",
                    "DNSName": "payments-edge.example.amazonaws.com",
                    "State": {"Code": "active"},
                    "AvailabilityZones": [{"SubnetId": "subnet-a"}, {"SubnetId": "subnet-b"}],
                    "SecurityGroups": ["sg-lb"],
                    "VpcId": "vpc-123",
                }
            ]
        }

    def describe_listeners(self, LoadBalancerArn: str):
        return {
            "Listeners": [
                {
                    "ListenerArn": "listener-arn",
                    "Port": 443,
                    "Protocol": "HTTPS",
                    "DefaultActions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/payments-api/abcdef",
                        }
                    ],
                }
            ]
        }


class FakeIAMClient:
    def get_role(self, RoleName: str):
        assume_role = {
            "Statement": [
                {
                    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                }
            ]
        }
        return {"Role": {"RoleName": RoleName, "Arn": f"arn:aws:iam::123456789012:role/{RoleName}", "AssumeRolePolicyDocument": assume_role}}

    def list_attached_role_policies(self, RoleName: str):
        if RoleName == "payments-task-execution-role":
            return {"AttachedPolicies": [{"PolicyName": "CloudWatchLogsFullAccess"}]}
        return {"AttachedPolicies": [{"PolicyName": "AmazonSSMManagedInstanceCore"}]}

    def get_instance_profile(self, InstanceProfileName: str):
        return {"InstanceProfile": {"Roles": [{"Arn": "arn:aws:iam::123456789012:role/payments-ec2-role"}]}}


class FakeEC2Client:
    def describe_instances(self, InstanceIds: list[str] | None = None, Filters: list[dict] | None = None):
        instance_ids = InstanceIds or ["i-0123456789abcdef0"]
        return {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": instance_ids[0],
                            "State": {"Name": "running"},
                            "InstanceType": "t3.large",
                            "SubnetId": "subnet-ec2",
                            "VpcId": "vpc-123",
                            "SecurityGroups": [{"GroupId": "sg-ec2"}],
                            "IamInstanceProfile": {"Arn": "arn:aws:iam::123456789012:instance-profile/payments-ec2-profile"},
                        }
                    ]
                }
            ]
        }

    def describe_instance_status(self, InstanceIds: list[str], IncludeAllInstances: bool):
        return {
            "InstanceStatuses": [
                {
                    "InstanceId": InstanceIds[0],
                    "InstanceStatus": {"Status": "impaired"},
                    "SystemStatus": {"Status": "ok"},
                }
            ]
        }

    def describe_route_tables(self, Filters: list[dict]):
        return {
            "RouteTables": [
                {
                    "RouteTableId": "rtb-123",
                    "Routes": [{"DestinationCidrBlock": "0.0.0.0/0", "State": "blackhole"}],
                }
            ]
        }

    def describe_security_groups(self, GroupIds: list[str]):
        return {
            "SecurityGroups": [
                {
                    "GroupId": GroupIds[0],
                    "IpPermissionsEgress": [],
                }
            ]
        }

    def describe_network_acls(self, Filters: list[dict]):
        return {
            "NetworkAcls": [
                {
                    "NetworkAclId": "acl-123",
                    "Entries": [{"RuleAction": "deny", "Protocol": "-1"}],
                }
            ]
        }

    def describe_vpc_attribute(self, VpcId: str, Attribute: str):
        if Attribute == "enableDnsSupport":
            return {"EnableDnsSupport": {"Value": True}}
        return {"EnableDnsHostnames": {"Value": False}}


class FakeEKSClient:
    def describe_cluster(self, name: str):
        return {
            "cluster": {
                "name": name,
                "status": "ACTIVE",
                "version": "1.29",
                "identity": {"oidc": {"issuer": "https://oidc.eks.example"}},
                "roleArn": "arn:aws:iam::123456789012:role/eks-cluster-role",
                "resourcesVpcConfig": {
                    "endpointPublicAccess": False,
                    "subnetIds": ["subnet-eks-a", "subnet-eks-b"],
                    "securityGroupIds": ["sg-eks"],
                    "vpcId": "vpc-123",
                },
                "health": {"issues": []},
            }
        }

    def list_nodegroups(self, clusterName: str):
        return {"nodegroups": ["payments-ng-a"]}

    def describe_nodegroup(self, clusterName: str, nodegroupName: str):
        return {
            "nodegroup": {
                "nodegroupName": nodegroupName,
                "status": "DEGRADED",
                "amiType": "AL2_x86_64",
                "scalingConfig": {"desiredSize": 3, "minSize": 1, "maxSize": 6},
                "health": {"issues": [{"code": "ClusterUnreachable"}]},
            }
        }

    def list_addons(self, clusterName: str):
        return {"addons": ["vpc-cni"]}

    def describe_addon(self, clusterName: str, addonName: str):
        return {
            "addon": {
                "addonName": addonName,
                "status": "DEGRADED",
                "addonVersion": "v1.18.3-eksbuild.1",
                "health": {"issues": [{"code": "InsufficientNumberOfReplicas"}]},
            }
        }


class FakeRDSClient:
    def describe_db_instances(self, DBInstanceIdentifier: str | None = None):
        identifier = DBInstanceIdentifier or "payments-prod-db"
        return {
            "DBInstances": [
                {
                    "DBInstanceIdentifier": identifier,
                    "DBInstanceStatus": "modifying",
                    "Engine": "postgres",
                    "MultiAZ": True,
                    "PubliclyAccessible": False,
                    "StorageEncrypted": True,
                    "AllocatedStorage": 100,
                    "PendingModifiedValues": {"DBInstanceClass": "db.r6g.large"},
                    "DBSubnetGroup": {
                        "VpcId": "vpc-123",
                        "Subnets": [{"SubnetIdentifier": "subnet-rds-a"}, {"SubnetIdentifier": "subnet-rds-b"}],
                    },
                    "VpcSecurityGroups": [{"VpcSecurityGroupId": "sg-rds"}],
                }
            ]
        }


class FakeEFSClient:
    def describe_file_systems(self, FileSystemId: str | None = None):
        if FileSystemId == "fs-all" or FileSystemId is None:
            return {"FileSystems": [{"FileSystemId": "fs-all"}]}
        return {
            "FileSystems": [
                {
                    "FileSystemId": FileSystemId,
                    "LifeCycleState": "available",
                    "Encrypted": True,
                    "PerformanceMode": "generalPurpose",
                    "VpcId": "vpc-123",
                }
            ]
        }

    def describe_mount_targets(self, FileSystemId: str):
        return {
            "MountTargets": [
                {
                    "MountTargetId": "mt-1",
                    "SubnetId": "subnet-a",
                }
            ]
        }

    def describe_mount_target_security_groups(self, MountTargetId: str):
        return {"SecurityGroups": ["sg-efs"]}


class FakeServiceQuotasClient:
    def list_service_quotas(self, ServiceCode: str, MaxResults: int, NextToken: str | None = None):
        quotas = {
            "ecs": [{"QuotaName": "Services per cluster", "Value": 100}],
            "ec2": [{"QuotaName": "Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances", "Value": 20}],
            "elasticloadbalancing": [
                {"QuotaName": "Application Load Balancers per Region", "Value": 50},
                {"QuotaName": "Target Groups per Region", "Value": 3000},
            ],
            "rds": [{"QuotaName": "DB instances", "Value": 40}],
            "efs": [{"QuotaName": "File systems per region", "Value": 1000}],
        }
        return {"Quotas": quotas.get(ServiceCode, [])}


def test_live_collector_collects_ecs_lb_iam_and_dependencies() -> None:
    collector = AWSLiveCollector(
        region_name="us-east-1",
        clients={
            "sts": FakeSTSClient(),
            "ecr": FakeECRClient(),
            "secretsmanager": FakeSecretsManagerClient(),
            "ssm": FakeSSMClient(),
            "cloudwatch": FakeCloudWatchClient(),
            "ecs": FakeECSClient(),
            "elbv2": FakeELBV2Client(),
            "iam": FakeIAMClient(),
            "efs": FakeEFSClient(),
            "ec2": FakeEC2Client(),
        },
    )

    snapshot = collector.collect_snapshot(
        environment="prod",
        workload_type="ecs",
        workload_name="payments-api",
        cluster="prod-apps",
        ecs_service="payments-api",
        collect_quotas=False,
    )

    assert snapshot["dependencies"]["sts"] == "ok"
    assert snapshot["dependencies"]["secrets_manager"] == "access_denied"
    assert snapshot["ecs"]["service_running_count"] == 1
    assert snapshot["alb"]["target_groups"][0]["unhealthy_targets"] == 1
    assert snapshot["iam"]["task_execution_role"] == "missing_ecr_permissions"
    assert snapshot["efs"]["file_systems"][0]["mount_target_count"] == 1
    assert snapshot["metadata"]["alarm_events"][0]["name"] == "payments-api-5xx"
    assert snapshot["metadata"]["deploy_events"][0]["source"] == "ecs"
    assert snapshot["network"]["route_mismatch"] is True


def test_live_collector_collects_ec2_eks_and_rds() -> None:
    collector = AWSLiveCollector(
        region_name="us-east-1",
        clients={
            "cloudwatch": FakeCloudWatchClient(),
            "ec2": FakeEC2Client(),
            "eks": FakeEKSClient(),
            "rds": FakeRDSClient(),
            "iam": FakeIAMClient(),
            "service-quotas": FakeServiceQuotasClient(),
            "ecs": FakeECSClient(),
            "elbv2": FakeELBV2Client(),
            "efs": FakeEFSClient(),
        },
    )

    snapshot = collector.collect_snapshot(
        environment="prod",
        workload_type="service",
        workload_name="payments-platform",
        ec2_instance_ids=["i-0123456789abcdef0"],
        eks_cluster_name="payments-eks-prod",
        rds_instance_ids=["payments-prod-db"],
        collect_dependencies=False,
        collect_quotas=True,
    )

    assert snapshot["ec2"]["instances"][0]["instance_status"] == "impaired"
    assert snapshot["eks"]["nodegroups"][0]["status"] == "DEGRADED"
    assert snapshot["rds"]["instances"][0]["storage_utilization"] == 0.75
    assert snapshot["iam"]["irsa"] == "ok"
    assert snapshot["network"]["sg_mismatch"] is True
    assert snapshot["network"]["nacl_mismatch"] is True
    assert snapshot["network"]["dns_private_resolution"] == "fail"
    assert any(item["name"] == "DB instances" for item in snapshot["quotas"])
