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
4. Rode testes basicos para STS/ECR/Secrets/SSM/CloudWatch
5. Registre apenas os sintomas confirmados
6. Execute:

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
