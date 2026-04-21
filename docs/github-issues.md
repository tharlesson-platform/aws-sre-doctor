# Export para GitHub Issues

O `aws-sre-doctor` agora consegue transformar um relatório JSON em uma issue pronta para triagem, handoff ou acompanhamento de incidente.

## Fluxo recomendado

1. Gere o relatório:

```bash
aws-sre-doctor analyze \
  --input-path examples/incident_snapshot_multi_service.json \
  --environment prod \
  --report-name multi
```

2. Gere um preview local da issue:

```bash
aws-sre-doctor export-github-issue \
  --report-path artifacts/multi.json \
  --repo tharlesson-platform/aws-sre-doctor \
  --preview-path artifacts/multi-github-issue.md \
  --dry-run
```

3. Se o corpo estiver bom, publique de verdade:

```bash
set GITHUB_TOKEN=ghp_xxx
aws-sre-doctor export-github-issue \
  --report-path artifacts/multi.json \
  --repo tharlesson-platform/aws-sre-doctor \
  --label incident \
  --label sre-doctor
```

## O que entra na issue

- resumo executivo
- severidade e health score
- próximos passos sugeridos
- hipóteses correlacionadas
- relatório completo em markdown

## Quando isso ajuda mais

- handoff entre turnos
- registrar incidentes que começaram fora do horário do time principal
- abrir backlog técnico com contexto suficiente
- compartilhar um diagnóstico inicial com engenharia, plataforma e liderança

## Erros comuns

- tentar publicar sem `GITHUB_TOKEN`
- passar um `report-path` em markdown ou html em vez do JSON gerado por `analyze`
- publicar direto sem olhar o preview primeiro
