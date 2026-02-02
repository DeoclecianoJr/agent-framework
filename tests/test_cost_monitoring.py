"""Tests for cost monitoring and alerting system."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.core.cost_monitoring import CostMonitor, CostReporter, CostAlert


class TestCostAlert:
    """Test CostAlert class."""
    
    def test_cost_alert_creation(self):
        alert = CostAlert("daily", 10.0, 15.0, agent_id="test_agent")
        
        assert alert.threshold_type == "daily"
        assert alert.threshold_value == 10.0
        assert alert.current_value == 15.0
        assert alert.agent_id == "test_agent"
        assert alert.session_id is None
        assert isinstance(alert.timestamp, datetime)


class TestCostMonitor:
    """Test CostMonitor class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        return db
    
    @pytest.fixture
    def cost_monitor(self, mock_db):
        """Create CostMonitor instance."""
        return CostMonitor(mock_db)
    
    def test_configure_thresholds(self, cost_monitor):
        """Test threshold configuration."""
        cost_monitor.configure_thresholds(
            daily=20.0,
            monthly=200.0,
            session=10.0,
            agent_daily=15.0
        )
        
        assert cost_monitor.daily_threshold == 20.0
        assert cost_monitor.monthly_threshold == 200.0
        assert cost_monitor.session_threshold == 10.0
        assert cost_monitor.agent_daily_threshold == 15.0
    
    def test_configure_partial_thresholds(self, cost_monitor):
        """Test partial threshold configuration."""
        original_daily = cost_monitor.daily_threshold
        
        cost_monitor.configure_thresholds(monthly=250.0)
        
        assert cost_monitor.daily_threshold == original_daily  # Unchanged
        assert cost_monitor.monthly_threshold == 250.0
    
    def test_get_cost_summary_structure(self, cost_monitor, mock_db):
        """Test cost summary structure."""
        # Mock database queries
        mock_db.query.return_value.filter.return_value.scalar.return_value = 5.0
        
        summary = cost_monitor.get_cost_summary()
        
        assert "daily_cost" in summary
        assert "monthly_cost" in summary
        assert "thresholds" in summary
        assert "status" in summary
        assert "timestamp" in summary
    
    def test_check_cost_thresholds_no_alerts(self, cost_monitor, mock_db):
        """Test threshold checking with no alerts."""
        # Mock low costs
        mock_db.query.return_value.filter.return_value.scalar.return_value = 1.0
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 1.0
        
        alerts = cost_monitor.check_cost_thresholds("session_1", "agent_1", 0.1)
        
        assert alerts == []
    
    def test_check_cost_thresholds_session_exceeded(self, cost_monitor, mock_db):
        """Test session threshold exceeded."""
        # Mock high session cost
        def mock_scalar_side_effect():
            # Return high session cost, low others
            return [10.0, 1.0, 1.0, 1.0]
        
        mock_db.query.return_value.filter.return_value.scalar.side_effect = [10.0, 1.0, 1.0]
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 1.0
        
        alerts = cost_monitor.check_cost_thresholds("session_1", "agent_1", 0.1)
        
        assert len(alerts) == 1
        assert alerts[0].threshold_type == "session"
        assert alerts[0].current_value == 10.0
        assert alerts[0].session_id == "session_1"


class TestCostReporter:
    """Test CostReporter class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        return db
    
    @pytest.fixture
    def cost_reporter(self, mock_db):
        """Create CostReporter instance."""
        return CostReporter(mock_db)
    
    def test_get_daily_report_structure(self, cost_reporter, mock_db):
        """Test daily report structure."""
        # Mock database results
        mock_daily_result = Mock()
        mock_daily_result.total_cost = 5.0
        mock_daily_result.message_count = 10
        mock_daily_result.total_tokens = 1000
        
        mock_agent_row = Mock()
        mock_agent_row.agent_id = "test_agent"
        mock_agent_row.agent_cost = 3.0
        mock_agent_row.agent_messages = 6
        
        mock_model_row = Mock()
        mock_model_row.model = "gpt-4o-mini"
        mock_model_row.model_cost = 2.0
        mock_model_row.model_messages = 4
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_daily_result
        mock_db.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_agent_row]
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_model_row]
        
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()
        
        reports = cost_reporter.get_daily_report(start_date, end_date)
        
        assert len(reports) >= 1
        report = reports[0]
        assert "date" in report
        assert "total_cost" in report
        assert "total_messages" in report
        assert "agents" in report
        assert "models" in report
    
    def test_get_top_cost_sessions_structure(self, cost_reporter, mock_db):
        """Test top cost sessions structure."""
        # Mock database result
        mock_row = Mock()
        mock_row.session_id = "session_1"
        mock_row.agent_id = "agent_1"
        mock_row.session_cost = 5.0
        mock_row.message_count = 10
        mock_row.last_activity = datetime.now()
        
        mock_db.query.return_value.join.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_row]
        
        sessions = cost_reporter.get_top_cost_sessions(10, 7)
        
        assert len(sessions) == 1
        session = sessions[0]
        assert session["session_id"] == "session_1"
        assert session["agent_id"] == "agent_1"
        assert session["total_cost"] == 5.0


class TestCostMonitoringIntegration:
    """Integration tests for cost monitoring."""
    
    def test_end_to_end_cost_tracking(self, sqlite_memory_db):
        """Test complete cost tracking workflow."""
        from app.core.models import Message, Session
        
        # Create test session
        session = Session(
            id="test_session",
            agent_id="test_agent",
            attrs={}
        )
        sqlite_memory_db.add(session)
        
        # Create test messages with costs
        message1 = Message(
            id="msg1",
            session_id="test_session",
            role="user",
            content="Hello",
            attrs={},
            cost=2.0,
            model="gpt-4o-mini"
        )
        
        message2 = Message(
            id="msg2", 
            session_id="test_session",
            role="assistant",
            content="Hi there",
            attrs={},
            cost=3.0,
            model="gpt-4o-mini"
        )
        
        sqlite_memory_db.add_all([message1, message2])
        sqlite_memory_db.commit()
        
        # Test cost monitoring
        cost_monitor = CostMonitor(sqlite_memory_db)
        cost_monitor.configure_thresholds(session=1.0)  # Low threshold to trigger alert
        
        alerts = cost_monitor.check_cost_thresholds("test_session", "test_agent", 1.0)
        
        # Should trigger session threshold alert
        session_alerts = [a for a in alerts if a.threshold_type == "session"]
        assert len(session_alerts) == 1
        assert session_alerts[0].current_value == 5.0  # 2.0 + 3.0
        
        # Test cost reporter
        cost_reporter = CostReporter(sqlite_memory_db)
        top_sessions = cost_reporter.get_top_cost_sessions(5, 1)
        
        assert len(top_sessions) == 1
        assert top_sessions[0]["session_id"] == "test_session"
        assert top_sessions[0]["total_cost"] == 5.0
    
    def test_cost_summary_with_real_data(self, sqlite_memory_db):
        """Test cost summary with real database data."""
        from app.core.models import Message, Session
        
        # Create test data for multiple days
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        
        session = Session(
            id="test_session_2",
            agent_id="test_agent_2", 
            attrs={}
        )
        sqlite_memory_db.add(session)
        
        # Today's messages
        msg_today = Message(
            id="msg_today",
            session_id="test_session_2",
            role="assistant", 
            content="Today's response",
            attrs={},
            cost=4.0,
            model="gpt-4o",
            created_at=datetime.combine(today, datetime.min.time())
        )
        
        # Yesterday's messages
        msg_yesterday = Message(
            id="msg_yesterday",
            session_id="test_session_2", 
            role="assistant",
            content="Yesterday's response",
            attrs={},
            cost=6.0,
            model="gpt-4o",
            created_at=datetime.combine(yesterday, datetime.min.time())
        )
        
        sqlite_memory_db.add_all([msg_today, msg_yesterday])
        sqlite_memory_db.commit()
        
        # Test cost summary
        cost_monitor = CostMonitor(sqlite_memory_db)
        summary = cost_monitor.get_cost_summary("test_agent_2")
        
        assert summary["daily_cost"] == 4.0  # Today only
        assert summary["agent_daily_cost"] == 4.0
        assert "thresholds" in summary
        assert "status" in summary