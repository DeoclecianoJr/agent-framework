import pytest
from click.testing import CliRunner
from ai_framework.cli import cli
from ai_framework.decorators import agent
from ai_framework.agent import AgentRegistry

def test_cli_list_agents():
    # Clear registry for clean test
    AgentRegistry.instance()._agents = {}
    
    @agent(name="test-cli-agent", description="Test CLI Agent")
    def my_handler():
        pass
        
    runner = CliRunner()
    result = runner.invoke(cli, ["list-agents"])
    
    assert result.exit_code == 0
    assert "test-cli-agent" in result.output
    assert "Test CLI Agent" in result.output

def test_cli_chat_not_found():
    runner = CliRunner()
    result = runner.invoke(cli, ["chat", "non-existent-agent"], input="exit\n")
    
    # It might fail with error message before reading input
    assert "Error: Agent 'non-existent-agent' not found." in result.output

# Mocking LLM for chat test would be better but requires more setup.
# This ensures the basic command structure is correct.
