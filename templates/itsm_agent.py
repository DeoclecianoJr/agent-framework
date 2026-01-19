from ai_framework.decorators import agent

@agent(
    name="itsm-agent", 
    description="Assistant for IT Service Management, capable of opening tickets and checking status.",
    config={"department": "IT Support"}
)
async def itsm_handler(message: str, history: list):
    """
    ITSM specialized handler.
    In a real scenario, this agent would have tools to interact with Jira, ServiceNow, etc.
    """
    return "I can help you open a support ticket or check the status of your existing requests."
