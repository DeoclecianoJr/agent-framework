---
task_id: 03
name: Configuração e validação do Alembic
week: 1
status: pendente
related_FRs: [FR96, FR91]
related_NFRs: []
---

## Descrição
Configurar Alembic, criar migration inicial e garantir que aplica corretamente no banco de dados.

## Sub-tarefas
- Configurar `alembic.ini` e diretório `migrations/`
- Gerar migration inicial
- Rodar migration em banco de teste

## Critérios de Aceite
- Migration aplica sem erros
- Banco de teste reflete modelos

## FRs/NFRs Relacionados
- FR96: Migrações automáticas
- FR91: Operações Docker

## Escopo de Testes
- **Integração:**
  - `test_alembic_migration_applies()` — executa `alembic upgrade head` e valida schema

## Exemplo de Teste de Integração
```python
def test_alembic_migration_applies():
    import subprocess
    result = subprocess.run(['alembic', 'upgrade', 'head'])
    assert result.returncode == 0
```
