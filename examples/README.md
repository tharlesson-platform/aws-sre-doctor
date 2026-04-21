# Examples

Use estes exemplos como ponto de partida antes de tentar montar um snapshot real do zero.

## Ordem recomendada

1. Rode o caso saudavel para confirmar que a CLI esta instalada corretamente.
2. Rode o caso degradado para ver o tipo de diagnostico esperado.
3. Gere um snapshot proprio com `init-snapshot` e adapte apenas os sintomas reais do incidente.

## Arquivos

- `incident_snapshot_healthy.json`
  - Cenario base sem falhas relevantes.
  - Comando:
    - `aws-sre-doctor analyze --input-path examples/incident_snapshot_healthy.json --environment prod --report-name healthy`
  - Saida esperada:
    - `artifacts/healthy.json`
    - `artifacts/healthy.md`
    - `artifacts/healthy.html`

- `incident_snapshot.json`
  - Cenario degradado com sinais em ECS, ALB, dependencias AWS, IAM, rede e quota.
  - Comando:
    - `aws-sre-doctor analyze --input-path examples/incident_snapshot.json --environment prod --report-name degraded`
  - Saida esperada:
    - `artifacts/degraded.json`
    - `artifacts/degraded.md`
    - `artifacts/degraded.html`

## Exemplo de colaboracao

Se alguem do time quiser criar um novo caso para treinamento:

```bash
aws-sre-doctor init-snapshot \
  --output-path examples/payments-stage.json \
  --environment stage \
  --workload-name payments-api \
  --cluster stage-apps
```

Depois basta editar o arquivo gerado e incluir apenas os sintomas que realmente interessam para o exercicio.
