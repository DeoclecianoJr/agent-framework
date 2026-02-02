"""Tests for guardrails system functionality."""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from ai_framework.core.guardrails import GuardrailProcessor, GuardrailViolation


class TestGuardrailProcessor:
    """Unit tests for GuardrailProcessor core functionality."""
    
    def test_init_with_all_parameters(self):
        """Test GuardrailProcessor initialization with all parameters."""
        llm_mock = Mock()
        blocklist = ["violence", "hate"]
        allowlist = ["technology", "education"]
        allowed_themes = ["ai", "framework"]
        tool_restrictions = {"agent1": ["search", "calculate"], "*": ["basic_tools"]}
        
        processor = GuardrailProcessor(
            llm=llm_mock,
            blocklist=blocklist,
            allowlist=allowlist,
            min_confidence=0.8,
            allowed_themes=allowed_themes,
            tool_restrictions=tool_restrictions
        )
        
        assert processor.llm == llm_mock
        assert processor.blocklist == blocklist
        assert processor.allowlist == allowlist
        assert processor.min_confidence == 0.8
        assert processor.allowed_themes == allowed_themes
        assert processor.tool_restrictions == tool_restrictions
    
    def test_init_with_defaults(self):
        """Test GuardrailProcessor initialization with default values."""
        llm_mock = Mock()
        
        processor = GuardrailProcessor(llm=llm_mock)
        
        assert processor.llm == llm_mock
        assert processor.blocklist == []
        assert processor.allowlist == []
        assert processor.min_confidence == 0.0
        assert processor.allowed_themes == []
        assert processor.tool_restrictions == {}
    
    def test_validate_input_clean(self):
        """Test validate_input with clean content."""
        llm_mock = Mock()
        processor = GuardrailProcessor(llm=llm_mock)
        
        # Should not raise any exception
        processor.validate_input("This is a clean message about technology.")
    
    def test_validate_input_blocklist_violation(self):
        """Test validate_input raises exception for blocklisted content."""
        llm_mock = Mock()
        processor = GuardrailProcessor(
            llm=llm_mock,
            blocklist=["violence", "hate"]
        )
        
        with pytest.raises(GuardrailViolation) as exc_info:
            processor.validate_input("This contains violence and harmful content.")
        
        assert "blocked topic" in str(exc_info.value).lower()
    
    def test_validate_input_allowlist_pass(self):
        """Test validate_input passes with allowlisted content."""
        llm_mock = Mock()
        processor = GuardrailProcessor(
            llm=llm_mock,
            allowlist=["technology", "education"]
        )
        
        # Should not raise any exception
        processor.validate_input("This is about technology and education.")
    
    def test_validate_input_allowlist_violation(self):
        """Test validate_input fails without allowlisted content."""
        llm_mock = Mock()
        processor = GuardrailProcessor(
            llm=llm_mock,
            allowlist=["technology", "education"]
        )
        
        with pytest.raises(GuardrailViolation) as exc_info:
            processor.validate_input("This is about cooking and recipes.")
        
        assert "does not contain any allowed topics" in str(exc_info.value)
    
    def test_validate_output_low_confidence(self):
        """Test validate_output with low confidence score."""
        llm_mock = Mock()
        processor = GuardrailProcessor(
            llm=llm_mock,
            min_confidence=0.7
        )
        
        result = processor.validate_output("Some response", confidence=0.5)
        
        assert "não tenho certeza suficiente" in result
    
    def test_validate_output_high_confidence(self):
        """Test validate_output with high confidence score."""
        llm_mock = Mock()
        processor = GuardrailProcessor(
            llm=llm_mock,
            min_confidence=0.7
        )
        
        result = processor.validate_output("Some response", confidence=0.9)
        
        assert result == "Some response"
    
    def test_validate_tool_usage_no_restrictions(self):
        """Test validate_tool_usage with no restrictions configured."""
        llm_mock = Mock()
        processor = GuardrailProcessor(llm=llm_mock)
        
        # Should allow any tool when no restrictions
        assert processor.validate_tool_usage("agent1", "any_tool") is True
        assert processor.validate_tool_usage("agent2", "another_tool") is True
    
    def test_validate_tool_usage_agent_specific(self):
        """Test validate_tool_usage with agent-specific restrictions."""
        llm_mock = Mock()
        processor = GuardrailProcessor(
            llm=llm_mock,
            tool_restrictions={
                "agent1": ["search", "calculate"],
                "agent2": ["translate"]
            }
        )
        
        # Agent1 should have access to allowed tools
        assert processor.validate_tool_usage("agent1", "search") is True
        assert processor.validate_tool_usage("agent1", "calculate") is True
        assert processor.validate_tool_usage("agent1", "translate") is False
        
        # Agent2 should have access to its allowed tools
        assert processor.validate_tool_usage("agent2", "translate") is True
        assert processor.validate_tool_usage("agent2", "search") is False
        
        # Agent3 not in restrictions should be allowed (opt-in model)
        assert processor.validate_tool_usage("agent3", "any_tool") is True
    
    def test_validate_tool_usage_global_restrictions(self):
        """Test validate_tool_usage with global restrictions (wildcard)."""
        llm_mock = Mock()
        processor = GuardrailProcessor(
            llm=llm_mock,
            tool_restrictions={
                "*": ["basic_search", "calculator"]
            }
        )
        
        # All agents should follow global restrictions if no specific config
        assert processor.validate_tool_usage("any_agent", "basic_search") is True
        assert processor.validate_tool_usage("any_agent", "calculator") is True
        assert processor.validate_tool_usage("any_agent", "advanced_tool") is False
    
    def test_validate_tool_usage_agent_overrides_global(self):
        """Test that agent-specific restrictions override global ones."""
        llm_mock = Mock()
        processor = GuardrailProcessor(
            llm=llm_mock,
            tool_restrictions={
                "*": ["basic_tool"],
                "agent1": ["advanced_tool", "expert_tool"]
            }
        )
        
        # Agent1 should use its specific restrictions
        assert processor.validate_tool_usage("agent1", "advanced_tool") is True
        assert processor.validate_tool_usage("agent1", "basic_tool") is False
        
        # Other agents should use global restrictions
        assert processor.validate_tool_usage("agent2", "basic_tool") is True
        assert processor.validate_tool_usage("agent2", "advanced_tool") is False
    
    def test_get_allowed_tools_no_restrictions(self):
        """Test get_allowed_tools with no restrictions."""
        llm_mock = Mock()
        processor = GuardrailProcessor(llm=llm_mock)
        
        result = processor.get_allowed_tools("agent1")
        assert result is None
    
    def test_get_allowed_tools_agent_specific(self):
        """Test get_allowed_tools with agent-specific restrictions."""
        llm_mock = Mock()
        processor = GuardrailProcessor(
            llm=llm_mock,
            tool_restrictions={
                "agent1": ["search", "calculate"],
                "*": ["basic_tool"]
            }
        )
        
        result = processor.get_allowed_tools("agent1")
        assert result == ["search", "calculate"]
        
        result2 = processor.get_allowed_tools("agent2")
        assert result2 == ["basic_tool"]
        
        # Returns copy, not reference
        result[0] = "modified"
        original = processor.get_allowed_tools("agent1")
        assert original == ["search", "calculate"]
    
    def test_from_config_complete(self):
        """Test from_config with complete configuration."""
        config = {
            "guardrails": {
                "blocklist": ["violence", "hate"],
                "allowlist": ["technology"],
                "min_confidence": 0.8,
                "allowed_themes": ["ai", "tech"],
                "tool_restrictions": {
                    "agent1": ["search"]
                }
            }
        }
        
        processor = GuardrailProcessor.from_config(config)
        
        assert processor.blocklist == ["violence", "hate"]
        assert processor.allowlist == ["technology"]
        assert processor.min_confidence == 0.8
        assert processor.allowed_themes == ["ai", "tech"]
        assert processor.tool_restrictions == {"agent1": ["search"]}
    
    def test_from_config_empty(self):
        """Test from_config with empty configuration."""
        config = {}
        
        processor = GuardrailProcessor.from_config(config)
        
        assert processor.blocklist == []  # Converts None to empty list in __init__
        assert processor.allowlist == []  # Converts None to empty list in __init__
        assert processor.min_confidence == 0.0
        assert processor.allowed_themes == []  # Converts None to empty list in __init__
        assert processor.tool_restrictions == {}
    
    def test_from_config_partial(self):
        """Test from_config with partial configuration."""
        config = {
            "guardrails": {
                "blocklist": ["spam"],
                "min_confidence": 0.6
                # Other fields missing
            }
        }
        
        processor = GuardrailProcessor.from_config(config)
        
        assert processor.blocklist == ["spam"]
        assert processor.allowlist == []  # Converts None to empty list in __init__
        assert processor.min_confidence == 0.6
        assert processor.allowed_themes == []  # Converts None to empty list in __init__
        assert processor.tool_restrictions == {}


class TestGuardrailViolation:
    """Test GuardrailViolation exception."""
    
    def test_exception_message(self):
        """Test GuardrailViolation exception message."""
        message = "This is blocked content"
        
        with pytest.raises(GuardrailViolation) as exc_info:
            raise GuardrailViolation(message)
        
        assert str(exc_info.value) == message
    
    def test_exception_inheritance(self):
        """Test GuardrailViolation inherits from Exception."""
        exception = GuardrailViolation("test")
        assert isinstance(exception, Exception)


class TestGuardrailIntegration:
    """Integration tests for guardrails with mock LLM."""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing."""
        mock = Mock()
        mock.generate = AsyncMock()
        return mock
    
    def test_comprehensive_validation_workflow(self, mock_llm):
        """Test complete validation workflow."""
        processor = GuardrailProcessor(
            llm=mock_llm,
            blocklist=["violence"],
            allowlist=["technology"],
            min_confidence=0.7,
            allowed_themes=["technology", "framework"],  # Include both themes
            tool_restrictions={"agent1": ["search", "calculate"]}
        )
        
        # Test content validation
        processor.validate_input("This is about technology and frameworks.")
        
        # Test blocked content
        with pytest.raises(GuardrailViolation):
            processor.validate_input("This contains violence.")
        
        # Test output validation with low confidence
        low_conf_result = processor.validate_output("Response", confidence=0.5)
        assert "não tenho certeza" in low_conf_result
        
        # Test output validation with high confidence
        high_conf_result = processor.validate_output("Good response", confidence=0.8)
        assert high_conf_result == "Good response"
        
        # Test tool validation
        assert processor.validate_tool_usage("agent1", "search") is True
        assert processor.validate_tool_usage("agent1", "forbidden_tool") is False
        assert processor.validate_tool_usage("agent2", "any_tool") is True  # No restrictions
        
        # Test allowed tools retrieval
        agent1_tools = processor.get_allowed_tools("agent1")
        assert agent1_tools == ["search", "calculate"]
        
        agent2_tools = processor.get_allowed_tools("agent2")
        assert agent2_tools is None
    
    def test_edge_cases(self, mock_llm):
        """Test edge cases and boundary conditions."""
        processor = GuardrailProcessor(llm=mock_llm)
        
        # Test empty content
        processor.validate_input("")
        
        # Test None content should not crash
        try:
            processor.validate_input(None)
        except (TypeError, AttributeError):
            pass  # Expected for None input
        
        # Test confidence edge cases
        result1 = processor.validate_output("test", confidence=0.0)
        assert result1 == "test"
        
        result2 = processor.validate_output("test", confidence=1.0)
        assert result2 == "test"
        
        # Test empty tool name
        assert processor.validate_tool_usage("agent1", "") is True