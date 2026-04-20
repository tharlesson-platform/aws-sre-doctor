# AWS SRE Doctor

CLI profissional para troubleshooting operacional em AWS, com foco em diagnóstico rápido e redução de MTTR.

## Problema que resolve

- Times de SRE perdem tempo consolidando sintomas espalhados entre ECS, ALB, IAM, quotas e rede.
- Incidentes recorrentes exigem hipóteses rápidas, severidade clara e próximos passos acionáveis.
- A ferramenta entrega um diagnóstico resumido e detalhado pronto para operação e handoff.

## Arquitetura

- CLI com Typer para execução local e futura automação em pipeline.
- Checks desacoplados em `checks/` para evoluir troubleshooting por domínio.
- Reporters em markdown/json/html para operação, documentação e portfólio técnico.

## Estrutura do projeto

```text
.
|-- cli/
|-- core/
|-- checks/
|-- reporters/
|-- config/
|-- tests/
|-- examples/
|-- docs/
|-- pyproject.toml
|-- Makefile
|-- .github/workflows/ci.yml
|-- README.md
|-- LICENSE
|-- NOTICE
```

## Como executar

```bash
python -m pip install -e .[dev]
aws-sre-doctor analyze --input-path examples/incident_snapshot.json --environment prod
```

## Exemplos reais

- `aws-sre-doctor analyze --input-path examples/incident_snapshot.json --environment prod`
- `AWS_REGION=us-east-1 AWS_PROFILE=platform aws-sre-doctor analyze --input-path examples/incident_snapshot.json --environment dev`

## Como isso ajuda SREs no dia a dia

- Acelera triagem inicial quando ECS, ALB e dependências AWS falham em conjunto.
- Padroniza diagnóstico resumido, causas prováveis e próximos passos para reduzir MTTR.
- Cria artefatos reutilizáveis em postmortems, runbooks e demos técnicas.

## Roadmap

- Coleta live via boto3 e integração opcional com Slack.
- Correlação automática com eventos de deploy e alarmes.
- Export de diagnóstico para GitHub Issues.

## Licença

Este projeto está licenciado sob a Apache License 2.0. Consulte o arquivo `LICENSE` para mais detalhes.

## Atribuição

Este projeto foi desenvolvido e publicado por **Tharlesson**.
Caso você utilize este material como base em ambientes internos, estudos, adaptações ou redistribuições, preserve os créditos de autoria e os avisos de licença aplicáveis.

## Créditos e Uso

Este repositório foi criado com foco em automação, padronização operacional e melhoria da rotina de profissionais de SRE, DevOps, Cloud e Plataforma.

Você pode:
- estudar
- reutilizar
- adaptar
- evoluir este projeto dentro do seu contexto

Ao reutilizar ou derivar este material:
- mantenha os avisos de licença
- preserve os créditos de autoria quando aplicável
- documente alterações relevantes feitas sobre a base original

## Autor

**Tharlesson**  
GitHub: https://github.com/tharlesson
