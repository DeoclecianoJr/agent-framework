"""Tests for agent and tool decorators."""
import asyncio

import pytest

from ai_framework.agent import AgentRegistry, get_agent
from ai_framework.decorators import agent, list_tools, tool
from ai_framework.llm import get_llm, count_tokens


def test_agent_decorator_registers_and_invokes():
    @agent(name="demo-agent", description="desc")
    def handler(x):
        return f"ok:{x}"

    registry = AgentRegistry.instance()
    definition = registry.get("demo-agent")

    assert definition.name == "demo-agent"
    assert definition.description == "desc"
    assert definition.handler("ping") == "ok:ping"


def test_agent_registry_overwrites_on_duplicate():
    @agent(name="dup-agent")
    def first(x):
        return f"first:{x}"

    @agent(name="dup-agent")
    def second(x):
        return f"second:{x}"

    definition = get_agent("dup-agent")
    assert definition.handler("v") == "second:v"


def test_get_agent_missing_raises():
    registry = AgentRegistry.instance()
    registry._agents.clear()  # reset state for isolation
    with pytest.raises(KeyError):
        registry.get("missing")


def test_tool_decorator_registers_and_invokes():
    @tool(description="sum two numbers")
    def add(a, b):
        return a + b

    tools = list_tools()
    assert "add" in tools
    assert tools["add"]["handler"](2, 3) == 5
    assert "sum two numbers" in tools["add"]["description"]


def test_mock_llm_chat_and_token_count():
    llm = get_llm("mock")
    result = asyncio.run(llm.chat([{"role": "user", "content": "hello"}]))

    assert result["content"] == "mock-response"
    assert result["provider"] == "mock"
    # result["messages"] was removed in favor of return format
    assert count_tokens("two words here") == 3
    assert count_tokens("") == 0

