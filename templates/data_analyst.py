from ai_framework.decorators import agent

@agent(
    name="data-analyst", 
    description="Agent specialized in data analysis, SQL generation, and trend reporting."
)
async def data_analyst_handler(message: str, history: list):
    """
    Data analyst handler.
    Typically uses tools like PythonREPL or SQLDatabase chain.
    """
    return "Please provide the dataset or the specific analytical question you have in mind."
