# Correções do Endpoint de Chat

## Problema Identificado
O endpoint `/chat/sessions` estava retornando **Internal Server Error** devido a um desalinhamento entre:
1. O modelo SQLAlchemy `Session` no código
2. A estrutura real da tabela `sessions` no banco de dados

## Erros Encontrados

### Erro 1: Coluna `summary` inexistente
- **Log**: `column sessions.summary does not exist`
- **Causa**: O modelo tinha `summary = Column(Text, nullable=True)` mas a tabela no banco não tinha essa coluna
- **Correção**: Removida a coluna `summary` do modelo em `app/core/models.py` (linha 65)

### Erro 2: Campo `title` sendo acessado incorretamente
- **Causa**: Código tentando acessar `session.title` e `session.is_active` que não existem no modelo
- **Correção**: Ajustado para armazenar `title` no campo JSON `attrs` e removido acesso a `is_active`

## Arquivos Modificados

### 1. `app/core/models.py`
**Removido**: Coluna `summary` do modelo Session

### 2. `app/repositories/session.py`
**Corrigido**: Método `create_session()` para:
- Adicionar import de `uuid`
- Gerar `id` explicitamente com `uuid.uuid4()`
- Armazenar `title` no campo JSON `attrs` em vez de coluna dedicada
- Remover referências a `is_active` e `metadata` (usar `attrs`)

### 3. `app/services/chat_service.py`
**Corrigido**: Método `create_session()` para:
- Buscar `title` de `session.attrs.get("title")`
- Usar `updated_at` em vez de `is_active`
- Incluir `metadata` do schema que mapeia para `attrs` do modelo

### 4. `app/api/chat.py`
**Corrigido**: Endpoint `list_chat_sessions()` para:
- Buscar `title` de `s.attrs.get("title")`
- Mapear corretamente todos os campos do modelo para o schema

## Estrutura Atual do Modelo Session

```python
class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True)
    agent_id = Column(String(255), ForeignKey("agents.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    attrs = Column(JSON, nullable=False, default={})  # Stores title and other metadata
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
```

## Como Aplicar as Correções

```bash
# Rebuild do container API
docker-compose build api

# Restart dos containers
docker-compose down && docker-compose up -d

# Aguardar inicialização
sleep 5

# Testar endpoint
curl -X GET "http://localhost:8000/chat/sessions" \
  -H "X-API-Key: ccc307ba25c5bf77d04af3850b7741c11388fd3ecf01c5171d6e85cede546abe"
```

## Resultado Esperado

```json
{
  "sessions": [],
  "total": 0,
  "limit": 100,
  "offset": 0
}
```

## Filosofia de Produção Aplicada

✅ **Nenhuma versão simplificada** - Corrigimos o desalinhamento real entre código e banco
✅ **Código production-ready** - Mapeamento correto de campos JSON para armazenar metadados
✅ **Arquitetura limpa** - Repository → Service → API mantida consistente
✅ **Sem workarounds** - Solução adequada usando campo JSON `attrs` para metadados flexíveis
