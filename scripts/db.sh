#!/bin/bash
# Database management script for AI Framework

set -e

# Load .env file - only database variables
if [ -f .env ]; then
    export POSTGRES_USER=$(grep "^POSTGRES_USER=" .env | cut -d '=' -f2)
    export POSTGRES_PASSWORD=$(grep "^POSTGRES_PASSWORD=" .env | cut -d '=' -f2)
    export POSTGRES_DB=$(grep "^POSTGRES_DB=" .env | cut -d '=' -f2)
    export POSTGRES_HOST=$(grep "^POSTGRES_HOST=" .env | cut -d '=' -f2)
    export POSTGRES_PORT=$(grep "^POSTGRES_PORT=" .env | cut -d '=' -f2)
fi

# Defaults
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
POSTGRES_DB=${POSTGRES_DB:-ai_framework_test}
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}

case "$1" in
    start)
        echo "🚀 Starting PostgreSQL with pgvector..."
        docker compose up -d
        echo "⏳ Waiting for database to be ready..."
        sleep 3
        echo "✅ PostgreSQL is running!"
        ;;
    
    stop)
        echo "🛑 Stopping PostgreSQL..."
        docker compose down
        echo "✅ PostgreSQL stopped!"
        ;;
    
    restart)
        echo "🔄 Restarting PostgreSQL..."
        docker compose restart
        echo "✅ PostgreSQL restarted!"
        ;;
    
    migrate)
        echo "📦 Running database migrations..."
        .venv/bin/alembic upgrade head
        echo "✅ Migrations complete!"
        ;;
    
    reset)
        echo "⚠️  WARNING: This will DELETE all data!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo "🗑️  Dropping schema..."
            docker exec ai_framework_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} \
                -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
            echo "📦 Running migrations..."
            .venv/bin/alembic upgrade head
            echo "✅ Database reset complete!"
        else
            echo "❌ Reset cancelled"
        fi
        ;;
    
    shell)
        echo "🐘 Opening PostgreSQL shell..."
        docker exec -it ai_framework_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}
        ;;
    
    status)
        echo "📊 Database Status:"
        docker ps | grep postgres || echo "❌ PostgreSQL is not running"
        echo ""
        echo "📋 Tables:"
        docker exec ai_framework_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "\dt" 2>/dev/null || echo "❌ Cannot connect to database"
        ;;
    
    test)
        echo "🧪 Running pgvector tests..."
        .venv/bin/pytest tests/test_pgvector_rag.py -v
        ;;
    
    *)
        echo "AI Framework - Database Management"
        echo ""
        echo "Usage: $0 {start|stop|restart|migrate|reset|shell|status|test}"
        echo ""
        echo "Commands:"
        echo "  start    - Start PostgreSQL container"
        echo "  stop     - Stop PostgreSQL container"
        echo "  restart  - Restart PostgreSQL container"
        echo "  migrate  - Run database migrations"
        echo "  reset    - Drop and recreate database (⚠️  deletes all data)"
        echo "  shell    - Open PostgreSQL shell"
        echo "  status   - Show database status"
        echo "  test     - Run pgvector tests"
        exit 1
        ;;
esac
