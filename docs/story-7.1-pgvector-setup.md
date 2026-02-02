# Story 7.1: PostgreSQL pgvector Extension Setup

## ✅ Status: COMPLETO

Implementação da Story 7.1 do Epic 7 (RAG & Knowledge Base) - PostgreSQL pgvector Extension Setup.

---

## 📋 Acceptance Criteria Validados

✅ **pgvector extension is enabled** (`CREATE EXTENSION IF NOT EXISTS vector`)  
✅ **knowledge_documents table is created** with vector column  
✅ **IVFFlat index can be created** for fast similarity search  
✅ **Table schema includes**: id, agent_id, source_type, source_id, file_name, content_chunk, embedding (vector 1536), attrs (JSONB), created_at, updated_at  
✅ **Foreign key to agents table** with cascade delete  
✅ **Cosine distance operator `<=>` works** successfully  

---

## 🏗️ Implementação

### 1. Dependências Adicionadas

**requirements-dev.txt:**
```txt
pgvector>=0.2.5
psycopg2-binary>=2.9.9
```

### 2. Modelos SQLAlchemy

**app/core/models.py:**

#### KnowledgeDocument
```python
class KnowledgeDocument(Base):
    """Document chunk with vector embeddings for RAG."""
    __tablename__ = "knowledge_documents"
    
    id = Column(String(36), primary_key=True)
    agent_id = Column(String(255), ForeignKey("agents.id", ondelete="CASCADE"))
    source_type = Column(String(50))  # 'google_drive', 'sharepoint', 'manual'
    source_id = Column(String(255))
    file_name = Column(String(500))
    content_chunk = Column(Text)
    chunk_index = Column(Integer, default=0)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small
    attrs = Column(JSON, default={})  # page_number, folder_path, etc.
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
```

#### KnowledgeSource
```python
class KnowledgeSource(Base):
    """Configuration for cloud knowledge sources."""
    __tablename__ = "knowledge_sources"
    
    id = Column(String(36), primary_key=True)
    agent_id = Column(String(255), ForeignKey("agents.id", ondelete="CASCADE"))
    source_type = Column(String(50))  # 'google_drive', 'sharepoint'
    config = Column(JSON)  # folder_id, access_token_encrypted, etc.
    last_sync_at = Column(DateTime(timezone=True))
    next_sync_at = Column(DateTime(timezone=True))
    sync_status = Column(String(50), default="pending")
    sync_errors = Column(JSON)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
```

### 3. Migration Alembic

**alembic/versions/ac7f27ba03af_add_pgvector_extension_and_rag_.py:**

```python
def upgrade():
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create knowledge_documents table with Vector column
    op.create_table('knowledge_documents', ...)
    
    # Create knowledge_sources table
    op.create_table('knowledge_sources', ...)

def downgrade():
    op.drop_table('knowledge_sources')
    op.drop_table('knowledge_documents')
    op.execute('DROP EXTENSION IF EXISTS vector')
```

**Nota**: IVFFlat index é criado após carga inicial de dados:
```sql
CREATE INDEX idx_kd_embedding_ivfflat 
ON knowledge_documents 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

### 4. Docker PostgreSQL com pgvector

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: ai_framework_postgres
    env_file:
      - .env
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-ai_framework_test}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

**Configuração via .env:**
```bash
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ai_framework_test
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Database URLs
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_framework_test
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_framework_test
```

**Script de Gerenciamento:**
```bash
# Iniciar PostgreSQL
./scripts/db.sh start

# Ver status
./scripts/db.sh status

# Aplicar migrations
./scripts/db.sh migrate

# Reset database (⚠️ deleta dados)
./scripts/db.sh reset

# Abrir shell PostgreSQL
./scripts/db.sh shell

# Rodar testes
./scripts/db.sh test
```

---

## 🧪 Testes

### Executar Testes

```bash
# 1. Subir PostgreSQL com pgvector
docker compose up -d

# 2. Aplicar migrations
.venv/bin/alembic upgrade head

# 3. Rodar testes
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_framework_test \
  .venv/bin/pytest tests/test_pgvector_rag.py -v
```

### Cobertura de Testes (11 testes, todos ✅)

#### TestPgvectorExtension
- ✅ `test_pgvector_extension_enabled` - Extensão pgvector habilitada
- ✅ `test_knowledge_documents_table_exists` - Tabela criada
- ✅ `test_knowledge_sources_table_exists` - Tabela criada
- ✅ `test_embedding_column_is_vector_type` - Coluna embedding é tipo vector
- ✅ `test_ivfflat_index_can_be_created` - Índice IVFFlat funciona

#### TestKnowledgeDocumentModel
- ✅ `test_create_knowledge_document_with_embedding` - Criar documento com embedding
- ✅ `test_agent_cascade_delete_removes_documents` - Cascade delete funciona

#### TestVectorSimilaritySearch
- ✅ `test_cosine_similarity_search` - Busca por similaridade cosine (<=>)
- ✅ `test_agent_isolation_in_vector_search` - Isolamento por agent_id

#### TestKnowledgeSourceModel
- ✅ `test_create_google_drive_source` - Configurar Google Drive
- ✅ `test_create_sharepoint_source` - Configurar SharePoint

---

## 📊 Resultados dos Testes

```
====================================== test session starts =======================================
collected 11 items                                                                               

tests/test_pgvector_rag.py::TestPgvectorExtension::test_pgvector_extension_enabled PASSED  [  9%]
tests/test_pgvector_rag.py::TestPgvectorExtension::test_knowledge_documents_table_exists PASSED [ 18%]
tests/test_pgvector_rag.py::TestPgvectorExtension::test_knowledge_sources_table_exists PASSED [ 27%]
tests/test_pgvector_rag.py::TestPgvectorExtension::test_embedding_column_is_vector_type PASSED [ 36%]
tests/test_pgvector_rag.py::TestPgvectorExtension::test_ivfflat_index_can_be_created PASSED [ 45%]
tests/test_pgvector_rag.py::TestKnowledgeDocumentModel::test_create_knowledge_document_with_embedding PASSED [ 54%]
tests/test_pgvector_rag.py::TestKnowledgeDocumentModel::test_agent_cascade_delete_removes_documents PASSED [ 63%]
tests/test_pgvector_rag.py::TestVectorSimilaritySearch::test_cosine_similarity_search PASSED [ 72%]
tests/test_pgvector_rag.py::TestVectorSimilaritySearch::test_agent_isolation_in_vector_search PASSED [ 81%]
tests/test_pgvector_rag.py::TestKnowledgeSourceModel::test_create_google_drive_source PASSED [ 90%]
tests/test_pgvector_rag.py::TestKnowledgeSourceModel::test_create_sharepoint_source PASSED [100%]

======================================= 11 passed in 1.59s =======================================
```

---

## 🔍 Exemplos de Uso

### Busca Semântica com Cosine Distance

```python
from sqlalchemy import text

# Buscar top 5 chunks mais similares ao query
query_embedding = [0.1, 0.2, ...] # 1536 dimensions

results = session.execute(
    text(f"""
        SELECT 
            id,
            file_name,
            content_chunk,
            1 - (embedding <=> '{query_embedding}'::vector) AS similarity
        FROM knowledge_documents
        WHERE agent_id = :agent_id
            AND 1 - (embedding <=> '{query_embedding}'::vector) > 0.7
        ORDER BY embedding <=> '{query_embedding}'::vector
        LIMIT 5
    """),
    {"agent_id": "my_agent"}
).fetchall()
```

### Criar Documento com Embedding

```python
from app.core.models import KnowledgeDocument
import numpy as np

embedding = np.random.rand(1536).tolist()

doc = KnowledgeDocument(
    agent_id="support_agent",
    source_type="google_drive",
    source_id="1ABC123XYZ",
    file_name="product_manual.pdf",
    content_chunk="This is a chunk of the product manual...",
    chunk_index=0,
    embedding=embedding,
    attrs={"page_number": 1, "folder": "Documentation"}
)

session.add(doc)
session.commit()
```

---

## 🚀 Próximos Passos

### Story 7.2: Embedding Provider Abstraction (LangChain)
- Suporte OpenAI, Gemini, Ollama embeddings
- Interface unificada via LangChain
- Fallback para HuggingFace local

### Story 7.3: Google Drive OAuth 2.0 Integration
- OAuth flow para Google Drive
- Token encryption (AES-256)
- Folder/file permissions

### Story 7.4: SharePoint/Microsoft Graph API OAuth
- Microsoft Graph API integration
- SharePoint site/library access
- Token management

---

## 📝 Notas Técnicas

### Por que pgvector?

- ✅ Unified storage (dados relacionais + vetores no mesmo PostgreSQL)
- ✅ ACID transactions
- ✅ Sub-300ms semantic search com IVFFlat (50k vectors)
- ✅ Sem infraestrutura adicional (ChromaDB, Pinecone, Qdrant)
- ✅ Compatível com SQLAlchemy ORM

### Dimensões do Embedding

- OpenAI `text-embedding-3-small`: **1536 dimensions**
- Google Gemini `embedding-001`: **768 dimensions**  
- Ollama `nomic-embed-text`: **768 dimensions**

**Decisão**: Usar 1536 (OpenAI) como padrão, com suporte futuro para dimensões variáveis.

### IVFFlat vs HNSW

| Índice | Build Time | Search Speed | Recall |
|--------|------------|--------------|--------|
| IVFFlat | Rápido | ~224ms (50k) | 95% |
| HNSW | Lento | <100ms (50k) | 99% |

**Decisão**: IVFFlat para MVP (build time rápido), HNSW para produção.

---

**Data de Implementação**: 2026-01-27  
**Desenvolvedor**: Winston (Arquiteto) + Wbj-compassuol-010  
**Status**: ✅ COMPLETO - Todos os acceptance criteria validados
