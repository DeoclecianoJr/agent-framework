import pytest
from ai_framework.decorators import tool
from ai_framework.core.tools import ToolRegistry
from langchain_core.tools import StructuredTool

def test_tool_registration():
    # Clear registry for clean test
    ToolRegistry.instance()._tools = {}
    
    @tool(name="calc", description="Performs calculation")
    def calculate(a: int, b: int) -> int:
        """Sums two numbers."""
        return a + b
        
    registry = ToolRegistry.instance()
    t_def = registry.get("calc")
    
    assert t_def.name == "calc"
    assert t_def.description == "Performs calculation"
    assert t_def.func(2, 3) == 5

def test_tool_to_langchain():
    # Clear registry
    ToolRegistry.instance()._tools = {}
    
    @tool()
    def my_tool(x: str):
        """My tool docs"""
        return x
        
    lc_tools = ToolRegistry.instance().to_langchain()
    assert len(lc_tools) == 1
    assert isinstance(lc_tools[0], StructuredTool)
    assert lc_tools[0].name == "my_tool"
    assert lc_tools[0].description == "My tool docs"

def test_tool_registry_singleton():
    reg1 = ToolRegistry.instance()
    reg2 = ToolRegistry.instance()
    assert reg1 is reg2
