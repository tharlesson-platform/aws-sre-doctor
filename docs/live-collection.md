# Coleta live com boto3

O `aws-sre-doctor` agora consegue montar um snapshot inicial diretamente a partir da AWS usando `boto3`.

O objetivo nao e substituir toda a investigacao manual.

O objetivo e acelerar o bootstrap do diagnostico, capturando estado inicial de:

- `ECS`
- `EC2`
- `EKS`
- `RDS`
- `Load Balancers`
- `Target Groups`
- `IAM roles`
- `EFS`
- `STS`, `ECR`, `Secrets Manager`, `SSM` e `CloudWatch`

## Pre-requisitos

- credenciais AWS validas
- permissao de leitura sobre os recursos que voce quer coletar
- `python -m pip install -e .[dev]`

## Fluxo basico

```bash
aws-sre-doctor collect-live \
  --output-path incident_snapshot.live.json \
  --environment prod \
  --region us-east-1 \
  --workload-type ecs \
  --workload-name payments-api \
  --cluster prod-apps \
  --ecs-service payments-api
```

Depois:

```bash
aws-sre-doctor analyze --input-path incident_snapshot.live.json --environment prod
```

## Exemplos por servico

### ECS

```bash
aws-sre-doctor collect-live \
  --output-path snapshots/payments-ecs.json \
  --environment prod \
  --region us-east-1 \
  --workload-type ecs \
  --workload-name payments-api \
  --cluster prod-apps \
  --ecs-service payments-api
```

### EC2

```bash
aws-sre-doctor collect-live \
  --output-path snapshots/payments-ec2.json \
  --environment prod \
  --region us-east-1 \
  --workload-type ec2 \
  --workload-name payments-ec2-fleet \
  --ec2-instance-id i-0123456789abcdef0 \
  --ec2-instance-id i-0123456789abcdef1
```

### EKS

```bash
aws-sre-doctor collect-live \
  --output-path snapshots/payments-eks.json \
  --environment prod \
  --region us-east-1 \
  --workload-type eks \
  --workload-name payments-cluster \
  --eks-cluster-name payments-eks-prod
```

### RDS

```bash
aws-sre-doctor collect-live \
  --output-path snapshots/payments-rds.json \
  --environment prod \
  --region us-east-1 \
  --workload-type rds \
  --workload-name payments-db \
  --rds-instance-id payments-prod-db
```

### Load Balancer e Target Group

```bash
aws-sre-doctor collect-live \
  --output-path snapshots/payments-edge.json \
  --environment prod \
  --region us-east-1 \
  --workload-type service \
  --workload-name payments-edge \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/payments-edge/123abc \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/payments-edge-tg/456def
```

### IAM e EFS

```bash
aws-sre-doctor collect-live \
  --output-path snapshots/payments-iam-efs.json \
  --environment prod \
  --region us-east-1 \
  --workload-type service \
  --workload-name payments-support \
  --iam-role-arn arn:aws:iam::123456789012:role/payments-task-execution-role \
  --iam-role-arn arn:aws:iam::123456789012:role/payments-irsa-role \
  --efs-file-system-id fs-0123456789abcdef0
```

## O que a coleta live ja faz bem

- consolidar estado inicial de varios recursos
- registrar dependencia de APIs AWS
- descobrir target groups, roles e EFS a partir de ECS quando possivel
- salvar um snapshot reutilizavel para handoff e postmortem

## O que ainda exige validacao humana

- concluir `route_mismatch`, `sg_mismatch` e `nacl_mismatch`
- confirmar causalidade entre mudanca e impacto
- fechar RCA final

## Erros comuns

- esquecer `--cluster` em ECS
- usar `--workload-type eks` sem `--eks-cluster-name`
- rodar com credencial sem permissao de leitura e interpretar `access_denied` como falha do servico
- coletar apenas um target group e esquecer o load balancer ou vice-versa
