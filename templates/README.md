# AI Framework Agent Templates

This directory contains ready-to-use agent templates for different use cases.

## Included Templates

1.  **Chatbot** (`chatbot.py`): A basic conversation agent.
2.  **ITSM Agent** (`itsm_agent.py`): Specialized in IT Service Management.
3.  **Data Analyst** (`data_analyst.py`): Designed for data exploration and reporting.

## How to use

To use these templates in your project, simply import them:

```python
from templates.chatbot import chat_handler
# This will automatically register the agent in the AgentRegistry
```

Then you can test them using the CLI:

```bash
export PYTHONPATH=$PYTHONPATH:.
python ai_framework/cli.py chat generic-chatbot
```
