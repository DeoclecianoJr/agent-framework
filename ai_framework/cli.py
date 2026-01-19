import click
import asyncio
import importlib
import sys
import os
from ai_framework.agent import AgentRegistry
from ai_framework.core.llm import get_llm
from ai_framework.core.executor import AgentExecutor
from ai_framework.core.memory import MemoryManager
from ai_framework.core.guardrails import GuardrailProcessor

def load_module(module_path: str):
    """Dynamically load a module to trigger registration."""
    try:
        if module_path.endswith(".py"):
            # Load from file path
            module_name = os.path.basename(module_path)[:-3]
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        else:
            # Load from module name
            importlib.import_module(module_path)
    except Exception as e:
        click.echo(f"Warning: Failed to load {module_path}: {e}")

@click.group()
@click.option("--include", "-i", multiple=True, help="Modules or files to include (to register agents).")
def cli(include):
    """AI Framework CLI Playground."""
    for item in include:
        load_module(item)

@cli.command()
def list_agents():
    """List all registered agents."""
    agents = AgentRegistry.instance().all()
    if not agents:
        click.echo("No agents registered.")
        return
    
    click.echo("Registered Agents:")
    for name, agent in agents.items():
        click.echo(f"- {name}: {agent.description or 'No description'}")

async def run_chat(agent_name: str):
    try:
        agent_def = AgentRegistry.instance().get(agent_name)
    except KeyError:
        click.echo(f"Error: Agent '{agent_name}' not found.")
        return

    click.echo(f"--- Chatting with {agent_name} ---")
    click.echo("Type 'exit' or 'quit' to stop.")
    
    # Initialize Executor with default components from settings
    from ai_framework.core.config import settings
    llm = get_llm(settings.llm_provider, model=settings.llm_model)
    memory = MemoryManager.create("buffer")
    
    # Load Guardrails from agent config if present
    guardrails = None
    if agent_def.config and "guardrails" in agent_def.config:
        guardrails = GuardrailProcessor.from_config(agent_def.config)
        
    executor = AgentExecutor(llm=llm, memory=memory, guardrails=guardrails)
    session_id = f"cli_{os.getpid()}"
    
    while True:
        user_input = click.prompt("You")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        try:
            # Execute through orchestrator to get tools, guardrails, and memory
            response = await executor.execute(
                session_id=session_id,
                message_content=user_input,
                use_tools=True, # Enable tool usage in CLI playground
                system_prompt=agent_def.config.get("system_prompt")
            )
            
            click.echo(f"{agent_name}: {response['content']}")
            
        except Exception as e:
            click.echo(f"Error: {str(e)}")

@cli.command()
@click.argument("agent_name")
def chat(agent_name: str):
    """Start an interactive chat with an agent."""
    asyncio.run(run_chat(agent_name))

if __name__ == "__main__":
    cli()
