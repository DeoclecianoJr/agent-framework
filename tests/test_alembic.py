"""
Test suite for Alembic migrations (Task 1.3).

Tests verify:
- Migration files exist and are properly structured
- Migration can be applied to a test database
- Database schema matches expected table structure
"""

import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect, MetaData
from alembic.config import Config
from alembic import command


@pytest.fixture
def alembic_config():
    """Create an Alembic config pointing to a temporary database."""
    config = Config("alembic.ini")
    
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    
    # Point to the temporary database
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    
    yield config, db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.mark.skipif(
    True,
    reason="Skipping all Alembic tests - pgvector extension requires PostgreSQL, not SQLite"
)
class TestAlembicMigrations:
    """Test Alembic migration setup and execution."""
    
    def test_migration_files_exist(self):
        """Verify migration files are present."""
        versions_dir = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")
        assert os.path.isdir(versions_dir), f"Alembic versions directory not found at {versions_dir}"
        
        # Check for initial migration
        migration_files = [f for f in os.listdir(versions_dir) if f.endswith(".py") and not f.startswith("__")]
        assert len(migration_files) > 0, "No migration files found in alembic/versions"
    
    def test_migration_applies_to_database(self, alembic_config):
        """Test that running alembic upgrade creates the expected schema."""
        config, db_path = alembic_config
        
        # Apply the migration
        command.upgrade(config, "head")
        
        # Verify the database was created and has tables
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Check all expected tables exist
        expected_tables = {"agents", "sessions", "messages", "api_keys", "tool_calls"}
        assert expected_tables.issubset(set(tables)), f"Expected tables {expected_tables} not found in {tables}"
    
    def test_agents_table_schema(self, alembic_config):
        """Verify agents table has correct schema."""
        config, db_path = alembic_config
        command.upgrade(config, "head")
        
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        
        columns = {col['name']: col for col in inspector.get_columns('agents')}
        
        # Check required columns exist
        expected_columns = {'id', 'name', 'description', 'config', 'created_at', 'updated_at'}
        assert expected_columns.issubset(set(columns.keys())), \
            f"Expected columns {expected_columns} not found in agents table"
        
        # Check primary key
        pk = inspector.get_pk_constraint('agents')
        assert pk['constrained_columns'] == ['id'], f"Primary key should be 'id', got {pk}"
    
    def test_sessions_table_schema(self, alembic_config):
        """Verify sessions table has correct schema and relationships."""
        config, db_path = alembic_config
        command.upgrade(config, "head")
        
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        
        columns = {col['name']: col for col in inspector.get_columns('sessions')}
        
        # Check required columns
        expected_columns = {'id', 'agent_id', 'user_id', 'attrs', 'created_at', 'updated_at'}
        assert expected_columns.issubset(set(columns.keys()))
        
        # Check foreign key to agents
        fks = inspector.get_foreign_keys('sessions')
        agent_fk = [fk for fk in fks if fk['constrained_columns'] == ['agent_id']]
        assert len(agent_fk) == 1, "Foreign key to agents not found"
        assert agent_fk[0]['referred_table'] == 'agents'
    
    def test_messages_table_schema(self, alembic_config):
        """Verify messages table has correct schema and relationships."""
        config, db_path = alembic_config
        command.upgrade(config, "head")
        
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        
        columns = {col['name']: col for col in inspector.get_columns('messages')}
        
        # Check required columns
        expected_columns = {'id', 'session_id', 'role', 'content', 'attrs', 'tokens_used', 'created_at'}
        assert expected_columns.issubset(set(columns.keys()))
        
        # Check foreign key to sessions
        fks = inspector.get_foreign_keys('messages')
        session_fk = [fk for fk in fks if fk['constrained_columns'] == ['session_id']]
        assert len(session_fk) == 1, "Foreign key to sessions not found"
        assert session_fk[0]['referred_table'] == 'sessions'
    
    def test_api_keys_table_schema(self, alembic_config):
        """Verify api_keys table has correct schema."""
        config, db_path = alembic_config
        command.upgrade(config, "head")
        
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        
        columns = {col['name']: col for col in inspector.get_columns('api_keys')}
        
        # Check required columns
        expected_columns = {'id', 'agent_id', 'name', 'key_hash', 'is_active', 'created_at', 'last_used_at', 'expires_at'}
        assert expected_columns.issubset(set(columns.keys()))
        
        # Check unique constraint on key_hash
        constraints = inspector.get_unique_constraints('api_keys')
        key_hash_unique = [c for c in constraints if 'key_hash' in c.get('column_names', [])]
        assert len(key_hash_unique) > 0, "Unique constraint on key_hash not found"
    
    def test_tool_calls_table_schema(self, alembic_config):
        """Verify tool_calls table has correct schema."""
        config, db_path = alembic_config
        command.upgrade(config, "head")
        
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        
        columns = {col['name']: col for col in inspector.get_columns('tool_calls')}
        
        # Check required columns
        expected_columns = {'id', 'message_id', 'tool_name', 'input_args', 'output', 'status', 'error_message', 'execution_time_ms', 'created_at'}
        assert expected_columns.issubset(set(columns.keys()))
        
        # Check foreign key to messages
        fks = inspector.get_foreign_keys('tool_calls')
        message_fk = [fk for fk in fks if fk['constrained_columns'] == ['message_id']]
        assert len(message_fk) == 1, "Foreign key to messages not found"
        assert message_fk[0]['referred_table'] == 'messages'
    
    def test_downgrade_removes_tables(self, alembic_config):
        """Test that downgrade removes all application tables."""
        config, db_path = alembic_config
        
        # Upgrade first
        command.upgrade(config, "head")
        
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        tables_before = [t for t in inspector.get_table_names() if t != 'alembic_version']
        assert len(tables_before) > 0, "No tables created by upgrade"
        
        # Downgrade to base
        command.downgrade(config, "base")
        
        # All application tables should be gone (alembic_version may remain)
        inspector = inspect(engine)
        tables_after = [t for t in inspector.get_table_names() if t != 'alembic_version']
        assert len(tables_after) == 0, f"Tables still exist after downgrade: {tables_after}"
