---
task_id: 15
name: Segurança e compliance (PII, rate limit, TLS)
week: 5
status: pendente
related_FRs: [FR71, FR72, FR73, FR74, FR75, FR76, FR77, FR78, FR79, FR80]
related_NFRs: [NFR-Security]
---

## Descrição
Implementar detecção/masking de PII, rate limiting por custo, HTTPS/TLS, logging de auditoria, headers de segurança e políticas de privacidade.

## Sub-tarefas
- Detectar e mascarar PII em mensagens
- Rate limiting por custo/token
- Enforce HTTPS/TLS em produção
- Logging de auditoria (criação de chave, modificação de agent)
- Headers de segurança (CORS, HSTS, etc)
- Endpoints de export/delete para GDPR

## Critérios de Aceite
- PII detectado e mascarado
- Rate limit por custo funciona
- HTTPS obrigatório em prod
- Auditoria registrada

## FRs/NFRs Relacionados
- FR71-FR80: Segurança/compliance
- NFR-Security: Proteção de dados

## Escopo de Testes
- **Unitário:**
  - `test_detect_email_in_message()`
  - `test_mask_detected_pii()`
- **Integração:**
  - `test_rate_limit_by_token_cost()`
  - `test_log_audit_entry()`
- **E2E:**
  - `test_gdpr_export_delete()`

## Exemplo de Teste Unitário
```python
def test_detect_email_in_message():
    ...
```
