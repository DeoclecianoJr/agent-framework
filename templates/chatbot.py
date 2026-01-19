from ai_framework.decorators import agent

@agent(name="generic-chatbot", description="A versatile chatbot for general conversation.")
async def chat_handler(message: str, history: list):
    """
    General purpose chatbot handler.
    Args:
        message (str): The incoming user message.
        history (list): Previous conversation turns.
    Returns:
        str: Response from the agent.
    """
    # Business logic goes here
    return f"Echo: {message}"
