---
task_id: 17
name: CI/CD - GitHub Actions e cobertura
week: 7
status: pendente
related_FRs: [FR91, FR92, FR93, FR94, FR95, FR96, FR97, FR98, FR99, FR100]
related_NFRs: [NFR-Maintainability, NFR-Testing]
---

## Descrição
Configurar pipeline GitHub Actions para rodar testes unitários, integração, E2E, cobertura ≥80%, lint, type check, build Docker, deploy Helm.

## Sub-tarefas
- Workflow `.github/workflows/test.yml`
- Rodar pytest (unit, integration, e2e)
- Checar cobertura (pytest-cov)
- Rodar Black, Flake8, mypy
- Build Docker image
- Deploy Helm chart (mock)
- Upload coverage para codecov

## Critérios de Aceite
- Pipeline executa todos os jobs
- Coverage ≥80% obrigatório
- Build Docker e Helm sem erro

## FRs/NFRs Relacionados
- FR91-FR100: Operações, deploy, CI/CD
- NFR-Maintainability, NFR-Testing

## Escopo de Testes
- **CI/CD:**
  - `test_github_actions_runs_all_jobs()`
  - `test_coverage_threshold_enforced()`
  - `test_docker_builds_successfully()`

## Exemplo de Teste CI/CD
```yaml
- name: Run unit tests
  run: pytest tests/unit/ -v --cov=app
```
