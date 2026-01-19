---
task_id: 01
name: Inicializar projeto com Cookiecutter FastAPI
week: 1
status: pendente
related_FRs: [FR1, FR81]
related_NFRs: []
---

## Descrição
Executar o cookiecutter starter para gerar o esqueleto do projeto com FastAPI, SQLAlchemy, Alembic, Docker e pytest.

## Sub-tarefas
- Instalar cookiecutter e dependências
- Executar comando cookiecutter
- Validar estrutura de pastas e arquivos
- Adicionar `requirements-dev.txt` com stack de testes
- Rodar `pytest` (smoke test)

## Critérios de Aceite
- Estrutura criada: `app/`, `main.py`, `alembic/`, `app/core/`, `app/api/`
- `requirements-dev.txt` presente
- `pytest` executa sem erros (mesmo sem testes)

## FRs/NFRs Relacionados
- FR1: Instalação
- FR81: Scaffold de endpoints API

## Escopo de Testes

### O que deve ser testado
- Estrutura de diretórios e arquivos essenciais criados corretamente
- Arquivo `requirements-dev.txt` presente e com dependências mínimas
- Projeto inicializa sem erros de importação
- `pytest` executa sem falhas (mesmo sem testes)

### Tipos de Teste
- **Unitário:**
  - Verificar existência de cada arquivo/pasta essencial
  - Validar conteúdo mínimo de `requirements-dev.txt`
- **Integração:**
  - Importar `app.main` e garantir ausência de erros
  - Rodar `pytest` e garantir exit code 0
- **E2E:**
  - Não aplicável
- **Performance:**
  - Não aplicável

### Casos de Sucesso
- Todos os arquivos e pastas esperados existem
- `requirements-dev.txt` contém pytest, fastapi, sqlalchemy
- Import de `app.main` não gera exceção
- `pytest` executa e retorna exit code 0

### Casos de Falha
- Arquivo/pasta essencial ausente (ex: `app/main.py`)
- `requirements-dev.txt` ausente ou incompleto
- Import de `app.main` gera erro
- `pytest` retorna exit code diferente de 0

### Cobertura Esperada
- 100% dos arquivos/pastas essenciais verificados
- 100% dos imports principais testados

### Exemplos de Testes
```python
import os
import subprocess


    assert os.path.exists('app/main.py')
    assert os.path.exists('alembic')
    assert os.path.exists('app/core')
    assert os.path.exists('app/api')

## Exemplo de Teste Unitário
    with open('requirements-dev.txt') as f:
        content = f.read()
    assert 'pytest' in content

```python
    import importlib
    importlib.import_module('app.main')

def test_scaffold_files_exist():
    result = subprocess.run(['pytest'], capture_output=True)
    assert result.returncode == 0
```
    import os
    assert os.path.exists('app/main.py')
    assert os.path.exists('alembic')
    assert os.path.exists('app/core')
    assert os.path.exists('app/api')
```
