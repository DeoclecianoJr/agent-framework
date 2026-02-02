import asyncio
from ai_framework.decorators import agent, tool

@tool(name="get_ticket_status", description="Busca o status de um ticket de suporte pelo ID.")

def get_ticket_status(ticket_id: str) -> str:
    """Mock ferramenta de suporte."""
    # Retorna um status fixo para demonstração
    statuses = {
        "123": "Em processamento",
        "456": "Resolvido",
        "789": "Aguardando cliente"
    }
    return f"O ticket {ticket_id} está: {statuses.get(ticket_id, 'Não encontrado')}"

@agent(
    name="support_pro",
    description="Agente assistente geral prestativo e versátil.",
    config={
        "system_prompt": "Você é um assistente prestativo e versátil. Responda perguntas sobre qualquer tópico de forma clara e direta, usando informações do contexto quando disponível. Se o usuário perguntar sobre tickets de suporte, use a ferramenta get_ticket_status.",
        "memory_strategy": "summary",
        "drive_folder": "RAG_Documents",
        "guardrails": {
            "blocklist": ["financeiro", "senha", "password"],
            "min_confidence": 0.3
        }
    }
)
def support_handler(message: str, history: list = None):
    # O handler é opcional quando usamos o AgentExecutor via CLI/API, 
    # pois o executor gerencia o loop de pensamento.
    pass

if __name__ == "__main__":
    print("Agent 'support_pro' definido. Use o CLI para interagir:")
    print("python -m ai_framework.cli -i examples/support_agent.py chat support_pro")
