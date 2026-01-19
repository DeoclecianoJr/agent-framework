---
task_id: 04
name: Middleware de autenticação por API Key
week: 1
status: pendente
related_FRs: [FR71, FR72, FR73, FR74, FR75, FR76, FR77, FR80]
related_NFRs: [NFR-Security]
---

## Descrição
Implementar middleware para autenticação via header `X-API-Key`, com hashing seguro e validação no banco. Incluir lógica básica de rate limiting (requests/minuto).

## Sub-tarefas
- Criar modelo `APIKey` com campo hash
- Middleware para validar header em todas as rotas protegidas
- Função utilitária para hash seguro (bcrypt ou argon2)
- Endpoint para criar e listar API Keys (admin)
- Implementar rate limiting simples (por chave)

## Critérios de Aceite
- Requisições sem `X-API-Key` retornam 401
- Chave válida é reconhecida e autenticada
- Hash nunca exposto na resposta
- Rate limit retorna 429 ao exceder limite

## FRs/NFRs Relacionados
- FR71: API key management
- FR76: Rate limiting
- FR80: Security headers
- NFR-Security: Não expor dados sensíveis

## Escopo de Testes
- **Unitário:**
  - `test_hash_api_key()` — verifica hash seguro
  - `test_api_key_not_exposed()` — hash não aparece em resposta
- **Integração:**
  - `test_api_requires_api_key()` — sem header retorna 401
  - `test_api_key_rate_limit()` — excede limite retorna 429
- **E2E:**
  - `test_api_key_full_flow()` — criar chave, autenticar, exceder limite

## Exemplo de Teste de Integração
```python
def test_api_requires_api_key(client):
    response = client.get('/agents')
    assert response.status_code == 401
```
