---
task_id: 18
name: Documentação e exemplos de uso
week: 8
status: pendente
related_FRs: [FR89, FR100]
related_NFRs: [NFR-Maintainability]
---

## Descrição
Criar documentação detalhada (README, exemplos, OpenAPI, guides), exemplos de uso, e checklist de revisão de código.

## Sub-tarefas
- README com instruções de uso e setup
- Exemplos de requests/responses
- Documentação OpenAPI revisada
- Guides para extensibilidade e testes
- Checklist de revisão de código

## Critérios de Aceite
- README completo e atualizado
- Exemplos funcionais
- OpenAPI cobre todos endpoints

## FRs/NFRs Relacionados
- FR89: OpenAPI
- FR100: Documentação
- NFR-Maintainability: Fácil de entender e usar

## Escopo de Testes
- **Unitário:**
  - `test_readme_includes_setup_instructions()`
- **Integração:**
  - `test_openapi_schema_valid()`
- **E2E:**
  - `test_example_request_response()`

## Exemplo de Teste Unitário
```python
def test_readme_includes_setup_instructions():
    ...
```
