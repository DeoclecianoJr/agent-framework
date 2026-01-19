"""Agent execution engine (skeleton).

Coordinates conversation history, LLM calls, and response persistence.
"""
import inspect
import uuid
from datetime import datetime, timezone

from typing import Any, Dict, List, Optional

from ai_framework.llm import BaseLLM, count_tokens
from ai_framework.core.memory import BaseMemory
from ai_framework.core.tools import ToolRegistry
from ai_framework.core.privacy import PIIProcessor
from ai_framework.core.guardrails import GuardrailProcessor, GuardrailViolation
from ai_framework.core.resilience import CircuitBreakerError


class AgentExecutor:
    """Executes agent logic for a given session and message."""

    def __init__(self, llm: BaseLLM, memory: Optional[BaseMemory] = None, guardrails: Optional[GuardrailProcessor] = None) -> None:
        self.llm = llm
        self.memory = memory
        self.pii_processor = PIIProcessor()
        self.guardrails = guardrails


    async def execute(
        self,
        session_id: str,
        message_content: str,
        history: Optional[List[Dict[str, str]]] = None,
        tool_registry: Optional[ToolRegistry] = None,
        mask_pii: bool = False,
        guardrails: Optional[GuardrailProcessor] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Process a user message and return the agent response.

        Args:
            session_id: The active session ID.
            message_content: The new user message text.
            history: Optional list of previous messages in the session (overrides self.memory).
            tool_registry: Optional tool registry to use for this execution.
            mask_pii: Whether to mask PII in the message before sending to LLM.
            guardrails: Optional guardrail processor for this execution.
            system_prompt: Optional system prompt to prepend to the conversation.
            **kwargs: Additional execution parameters.


        Returns:
            Dict containing response content, metadata, and token usage.
        """
        processor = guardrails or self.guardrails

        # 0. Guardrails Input Validation
        if processor:
            try:
                processor.validate_input(message_content)
            except GuardrailViolation as e:
                return {
                    "content": f"Desculpe, não posso ajudar com isso. (Bloqueado: {e.topic or 'Conteúdo impróprio'})",
                    "session_id": session_id,
                    "role": "assistant",
                    "metadata": {
                        "usage": {"total_tokens": 0, "cost": 0.0},
                        "guardrail_violation": True,
                        "topic": getattr(e, "topic", None)
                    },
                    "created_at": datetime.now(timezone.utc),
                }

        # 1. Mask PII if requested
        if mask_pii:
            message_content = self.pii_processor.mask(message_content)

        # 2. Add tool definitions if requested
        use_tools = kwargs.pop("use_tools", False)
        tools = []
        registry = tool_registry or ToolRegistry.instance()
        if tool_registry or use_tools:
            tools = registry.to_langchain()

        # 1. Prepare messages for LLM
        llm_messages = []

        if system_prompt:
            llm_messages.append({"role": "system", "content": system_prompt})
        
        # Priority: explicit history > self.memory > empty
        if history is not None:
            llm_messages.extend(history)
        elif self.memory is not None:
            llm_messages.extend(self.memory.get_messages())
        
        llm_messages.append({"role": "user", "content": message_content})

        # 3. Call LLM (Tool reasoning happens here if provider supports it)
        try:
            response = await self.llm.chat(llm_messages, tools=tools, **kwargs)
        except CircuitBreakerError as e:
            return {
                "content": "Desculpe, o serviço de inteligência artificial está temporariamente indisponível. Por favor, tente novamente em alguns instantes.",
                "session_id": session_id,
                "role": "assistant",
                "metadata": {
                    "usage": {"total_tokens": 0, "cost": 0.0},
                    "error": str(e),
                    "resilience_error": True
                },
                "created_at": datetime.now(timezone.utc),
            }
        except Exception as e:
            # General error handling for LLM calls
            return {
                "content": f"Ocorreu um erro ao processar sua solicitação: {str(e)}",
                "session_id": session_id,
                "role": "assistant",
                "metadata": {
                    "usage": {"total_tokens": 0, "cost": 0.0},
                    "error": str(e)
                },
                "created_at": datetime.now(timezone.utc),
            }

        total_usage = response.get("usage", {}).copy()
        
        # 4. Handle Tool Calls (Reasoning Loop)
        # Check for tool_calls in both 'raw' (LangChain object) and the dictionary itself
        tool_calls = response.get("tool_calls")
        raw_response = response.get("raw")
        if not tool_calls and raw_response and hasattr(raw_response, "tool_calls"):
            tool_calls = raw_response.tool_calls

        if tool_calls:
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                try:
                    tool_instance = registry.get(tool_name)

                    # Execute tool
                    if inspect.iscoroutinefunction(tool_instance.func):
                        tool_result = await tool_instance.func(**tool_args)
                    else:
                        tool_result = tool_instance.func(**tool_args)
                    
                    # Add tool result to messages and call LLM again for final answer
                    llm_messages.append({"role": "assistant", "content": f"Called tool {tool_name} with {tool_args}"})
                    llm_messages.append({"role": "system", "content": f"Tool {tool_name} returned: {tool_result}"})
                    
                    # Call LLM again
                    final_response = await self.llm.chat(llm_messages, **kwargs)
                    response = final_response
                    
                    # Accumulate usage
                    loop_usage = final_response.get("usage", {})
                    for key in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                        total_usage[key] = total_usage.get(key, 0) + loop_usage.get(key, 0)
                    total_usage["cost"] = total_usage.get("cost", 0.0) + loop_usage.get("cost", 0.0)

                except Exception as e:
                    response["content"] = f"Error executing tool {tool_name}: {str(e)}"




        content = response.get("content", "")

        # 5. Guardrails Output Validation
        if processor:
            content = processor.validate_output(
                content, 
                confidence=response.get("metadata", {}).get("confidence", 1.0)
            )

        # 6. Update memory if present
        if self.memory is not None:
            self.memory.add_message("user", message_content)
            self.memory.add_message("assistant", content)

        # 7. Metadata and usage
        return {
            "content": content,
            "session_id": session_id,
            "role": "assistant",
            "metadata": {
                "usage": total_usage,
                "provider": response.get("provider", "unknown"),
                "model": response.get("model", "unknown"),
                "guardrail_violation": response.get("metadata", {}).get("guardrail_violation", False)
            },
            "created_at": datetime.now(timezone.utc),
        }
