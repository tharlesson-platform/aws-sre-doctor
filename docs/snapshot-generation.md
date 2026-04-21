# Como gerar o `incident_snapshot` na pratica

O `incident_snapshot` nao precisa nascer de forma manual e abstrata.

O objetivo dele e consolidar os sintomas operacionais em um formato unico para o `aws-sre-doctor` analisar.

## Opcao 1: gerar uma base pronta

Crie um snapshot-base com a estrutura correta:

```bash
aws-sre-doctor init-snapshot \
  --output-path incident_snapshot.json \
  --environment prod \
  --workload-name payments-api \
  --cluster prod-apps
```

Isso gera um arquivo em estado saudavel. Depois voce altera apenas os campos que representam o incidente.

Se quiser um exemplo ja degradado para demo:

```bash
aws-sre-doctor init-snapshot \
  --output-path incident_snapshot.demo.json \
  --environment prod \
  --workload-name payments-api \
  --cluster prod-apps \
  --scenario ecs-degraded
```

## Opcao 2: preencher com dados reais do AWS CLI

Se voce preferir partir diretamente de boto3, consulte `docs/live-collection.md`.

### ECS service

Colete o estado do service:

```bash
aws ecs describe-services \
  --cluster prod-apps \
  --services payments-api
```

Mapeamento:

- `services[0].desiredCount` -> `ecs.service_desired_count`
- `services[0].runningCount` -> `ecs.service_running_count`
- quantidade de deploys com rollout nao concluido -> `ecs.deployments_in_progress`

### ECS tasks com falha

Liste tasks paradas e inspecione os motivos:

```bash
aws ecs list-tasks \
  --cluster prod-apps \
  --service-name payments-api \
  --desired-status STOPPED
```

```bash
aws ecs describe-tasks \
  --cluster prod-apps \
  --tasks <task-arn-1> <task-arn-2>
```

Mapeamento:

- `stoppedReason`
- erros de pull de imagem
- erros de secret na inicializacao

Esses dados entram em:

- `ecs.task_failures`
- `ecs.secrets_pull_errors`

### ALB target health

```bash
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>
```

Mapeamento:

- quantidade de `healthy` -> `alb.target_groups[*].healthy_targets`
- quantidade de `unhealthy` -> `alb.target_groups[*].unhealthy_targets`
- path do health check configurado -> `alb.target_groups[*].health_check_path`

### EC2

```bash
aws ec2 describe-instances --instance-ids i-0123456789abcdef0
aws ec2 describe-instance-status --instance-ids i-0123456789abcdef0 --include-all-instances
```

Mapeamento:

- `State.Name` -> `ec2.instances[*].state`
- `InstanceStatus.Status` -> `ec2.instances[*].instance_status`
- `SystemStatus.Status` -> `ec2.instances[*].system_status`
- `SecurityGroups[].GroupId` -> `ec2.instances[*].security_groups`

### EKS

```bash
aws eks describe-cluster --name payments-eks-prod
aws eks list-nodegroups --cluster-name payments-eks-prod
aws eks describe-nodegroup --cluster-name payments-eks-prod --nodegroup-name payments-ng-a
aws eks list-addons --cluster-name payments-eks-prod
aws eks describe-addon --cluster-name payments-eks-prod --addon-name vpc-cni
```

Mapeamento:

- `cluster.status` -> `eks.status`
- `nodegroup.status` -> `eks.nodegroups[*].status`
- `addon.status` -> `eks.addons[*].status`
- `identity.oidc.issuer` -> `iam.irsa`

### RDS

```bash
aws rds describe-db-instances --db-instance-identifier payments-prod-db
```

Mapeamento:

- `DBInstanceStatus` -> `rds.instances[*].status`
- `AllocatedStorage` -> `rds.instances[*].allocated_storage_gb`
- `PendingModifiedValues` -> `rds.instances[*].pending_modified_values`

### IAM

```bash
aws iam get-role --role-name payments-task-execution-role
aws iam list-attached-role-policies --role-name payments-task-execution-role
```

Mapeamento:

- attached policies -> `iam.roles[*].attached_policies`
- trust principal -> `iam.roles[*].trust_principals`
- findings manuais ou observados -> `iam.roles[*].findings`

### Reachability para APIs AWS

Rode a partir do workload, bastion ou ambiente equivalente:

```bash
aws sts get-caller-identity
aws ecr describe-repositories --max-items 1
aws secretsmanager list-secrets --max-items 1
aws ssm describe-parameters --max-items 1
aws cloudwatch describe-alarms --max-items 1
```

Mapeamento sugerido:

- sucesso -> `ok`
- timeout -> `timeout`
- permissao negada -> `access_denied`

### EFS mount

Se o mount falhou, copie a mensagem real:

```json
"efs": {
  "mount_error": "mount.nfs4: Connection timed out"
}
```

### Rede e DNS

Esses campos representam conclusoes operacionais, nao coleta automatica:

- `network.route_mismatch`
- `network.sg_mismatch`
- `network.nacl_mismatch`
- `network.dns_private_resolution`

Use `true` ou `fail` apenas quando voce realmente confirmar o problema.

### IAM

Exemplos uteis:

```json
"iam": {
  "task_execution_role": "missing_ecr_permissions",
  "irsa": "sts_assume_role_denied"
}
```

### Quotas

Registre so o que estiver perto do limite:

```json
"quotas": [
  {
    "name": "Fargate vCPU",
    "utilization": 0.94,
    "limit": 100
  }
]
```

## Exemplo de fluxo real

1. Gere a base com `init-snapshot`
2. Consulte `describe-services` e preencha ECS
3. Consulte `describe-target-health` e preencha ALB
4. Consulte EC2, EKS ou RDS quando fizerem parte do incidente
5. Rode testes basicos para STS/ECR/Secrets/SSM/CloudWatch
6. Registre apenas os sintomas confirmados
7. Execute:

```bash
aws-sre-doctor analyze --input-path incident_snapshot.json --environment prod
```

## Quando usar o exemplo pronto

Se voce estiver:

- fazendo demo
- treinando troubleshooting
- validando a instalacao da CLI
- mostrando a ferramenta em portfolio

Use `examples/incident_snapshot.json` ou `--scenario ecs-degraded`.
