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
from ai_framework.core.config import settings

import logging
logger = logging.getLogger(__name__)


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

        # Get history early for context-aware guardrails and LLM call
        history_msgs = []
        if history is not None:
            history_msgs = history
        elif self.memory is not None:
            history_msgs = await self.memory.get_messages()

        # 0. Guardrails Input Validation
        if processor and settings.guardrails_enabled:
            # Theme resolution: Merge agent-specific themes with global defaults
            local_themes = kwargs.get("allowed_themes", []) or processor.allowed_themes or []
            global_themes = settings.default_allowed_themes or []
            
            # Combine and unique lowercase themes
            merged_themes = list(set([t.lower() for t in local_themes] + [t.lower() for t in global_themes]))
            if merged_themes:
                processor.allowed_themes = merged_themes

            try:
                # Removed synchronous strict validation to improve performance and rely on LLM guidance
                # processor.validate_input(message_content)
                pass 
            except GuardrailViolation as e:
                # If it's a theme violation, try a semantic check with LLM before blocking
                is_off_topic = True
                if getattr(e, "is_theme_violation", False):
                    # Semantic Fallback: Ask LLM if this is really off-topic, considering history
                    themes_str = ", ".join(processor.allowed_themes)
                    
                    # Take only last 3-4 messages for the check to be efficient
                    recent_context = history_msgs[-4:] if history_msgs else []
                    context_str = "\n".join([f"{m['role']}: {m['content']}" for m in recent_context])
                    
                    check_prompt = [
                        {"role": "system", "content": f"You are a topic classifier. Is the following user message related to any of these themes: {themes_str}? \n\nConsider the conversation history below to resolve pronouns or context.\n\nHistory:\n{context_str}\n\nAnswer ONLY 'Yes' or 'No'."},
                        {"role": "user", "content": message_content}
                    ]
                    logger.debug(f"Guardrail Semantic Check: {message_content}")
                    try:
                        check_resp = await self.llm.chat(check_prompt, temperature=0.0)
                        logger.debug(f"Guardrail Check Response: {check_resp['content']}")
                        if "yes" in check_resp["content"].lower():
                            is_off_topic = False
                    except Exception:
                         is_off_topic = False
                
                if is_off_topic:
                    return {
                        "content": f"Desculpe, não posso ajudar com isso. (Bloqueado: {e.message})",
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
        
        # Add LLM-based Guardrails (Theme Enforcement via Prompt)
        if processor and processor.allowed_themes:
            themes_str = ", ".join(processor.allowed_themes)
            guardrail_prompt = (
                f"\n\nCRITICAL SAFETY RULE: You are ONLY allowed to discuss the following themes: {themes_str}. "
                "If the user message contains topics outside these themes (even if mixed with greetings), "
                "politely decline to answer the off-topic part and redirect them to the allowed topics. "
                "Common greetings and pleasantries are allowed."
            )
            if llm_messages and llm_messages[0]["role"] == "system":
                llm_messages[0]["content"] += guardrail_prompt
            else:
                llm_messages.insert(0, {"role": "system", "content": guardrail_prompt})

        # 2. Add history and current message
        llm_messages.extend(history_msgs)
        
        # ✅ RAG INTEGRATION: Search knowledge base for relevant context
        rag_context = ""
        if 'agent_id' in kwargs and kwargs['agent_id']:
            try:
                from app.core.dependencies import SessionLocal
                from app.core.models import KnowledgeDocument, KnowledgeSource
                
                # Get database session
                if SessionLocal is None:
                    logger.warning("RAG: Database not initialized, skipping RAG search")
                else:
                    db = SessionLocal()
                    try:
                        # Find agent's knowledge sources
                        agent_sources = db.query(KnowledgeSource).filter_by(
                            agent_id=kwargs['agent_id']
                        ).all()
                        
                        if agent_sources:
                            # Generate embedding for user query using same model as sync
                            try:
                                from sentence_transformers import SentenceTransformer
                                # Use multilingual model optimized for Portuguese
                                model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
                                
                                # Query Expansion: Add context from history for better semantic matching
                                query_text = message_content
                                if history_msgs and len(history_msgs) > 0:
                                    # Take last 2 messages for context
                                    recent_context = history_msgs[-2:]
                                    context_snippets = [msg['content'][:100] for msg in recent_context if msg.get('role') == 'user']
                                    if context_snippets:
                                        query_text = f"{' '.join(context_snippets)} {message_content}"
                                
                                logger.info(f"🔍 RAG QUERY: {query_text[:200]}")
                                query_embedding = model.encode(query_text, convert_to_numpy=True).tolist()
                                
                                # Use pgvector cosine similarity search
                                from sqlalchemy import text
                                
                                # Vector search query using pgvector <=> operator (cosine distance)
                                query = text("""
                                    SELECT id, content_chunk, file_name, attrs, 
                                           1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                                    FROM knowledge_documents
                                    WHERE agent_id = :agent_id
                                      AND embedding IS NOT NULL
                                    ORDER BY embedding <=> CAST(:query_embedding AS vector)
                                    LIMIT 10
                                """)
                                
                                # Format embedding as PostgreSQL array literal
                                embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
                                
                                result = db.execute(
                                    query,
                                    {
                                        "query_embedding": embedding_str,
                                        "agent_id": kwargs['agent_id']
                                    }
                                )
                                
                                documents = list(result.fetchall())
                                
                                if documents:
                                    # Build context from search results
                                    context_chunks = []
                                    logger.info(f"🔍 RAG DEBUG: Examining {len(documents)} documents from vector search")
                                    for idx, doc in enumerate(documents, 1):
                                        _, chunk, file_name, attrs, similarity = doc
                                        logger.info(f"RAG DEBUG: #{idx} File={file_name}, Similarity={similarity:.4f}, Chunk preview={chunk[:100].replace(chr(10), ' ')}")
                                        
                                        # Special debug for testador chunk
                                        if 'testador' in chunk.lower():
                                            logger.info(f"🎯 TESTADOR CHUNK FOUND: Position #{idx}, Similarity={similarity:.4f}")
                                        
                                        # Only include results with similarity > 0.25
                                        if similarity > 0.25:
                                            source_file = file_name or attrs.get('file_name', 'documento')
                                            # Limit chunk size for context (increased to 1000 to capture more content)
                                            chunk_text = chunk[:1000]
                                            context_chunks.append(f"[Fonte: {source_file} | Relevância: {similarity:.2f}] {chunk_text}")
                                    
                                    if context_chunks:
                                        rag_context = "\n\n".join(context_chunks)
                                        logger.info(f"✅ RAG: Found {len(context_chunks)} relevant chunks for agent {kwargs['agent_id']} using vector search")
                                        
                                        # DEBUG: Log context being sent to LLM
                                        has_testador = 'testador' in rag_context.lower()
                                        logger.info(f"📋 RAG CONTEXT CHECK: Sending {len(rag_context)} chars to LLM | Contains 'testador': {has_testador}")
                                        
                                        # Add RAG context to system message
                                        rag_system_msg = f"""
CONTEXTO RELEVANTE DA BASE DE CONHECIMENTO:
{rag_context}

Use essas informações da base de conhecimento para responder à pergunta do usuário quando relevante. Se a pergunta não estiver relacionada ao contexto fornecido, responda normalmente.
"""
                                        if llm_messages and llm_messages[0]["role"] == "system":
                                            llm_messages[0]["content"] += rag_system_msg
                                        else:
                                            llm_messages.insert(0, {"role": "system", "content": rag_system_msg})
                                    else:
                                        logger.info(f"RAG: No relevant chunks found (all similarities < 0.3)")
                                else:
                                    logger.info(f"RAG: No documents with embeddings found for agent {kwargs['agent_id']}")
                                    
                            except ImportError:
                                logger.warning("sentence-transformers not installed, falling back to text search")
                                # Fallback to old text search if sentence-transformers not available
                                pass
                            except Exception as embedding_error:
                                logger.warning(f"Vector search failed: {embedding_error}, skipping RAG")
                            
                    finally:
                        db.close()
                        
            except Exception as e:
                logger.warning(f"RAG search failed: {e}. Continuing without context.")
        
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
        # Preserve model information from LLM response
        if "model" not in total_usage:
            total_usage["model"] = response.get("model", self.llm.model)
        
        # 4. Handle Tool Calls (Reasoning Loop)
        max_loops = settings.max_tool_iterations
        loop_count = 0
        
        while loop_count < max_loops:
            # Check for tool_calls in both 'raw' (LangChain object) and the dictionary itself
            tool_calls = response.get("tool_calls")
            raw_response = response.get("raw")
            if not tool_calls and raw_response and hasattr(raw_response, "tool_calls"):
                tool_calls = raw_response.tool_calls

            if not tool_calls:
                break
                
            loop_count += 1
            tool_results_to_append = []
            
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # Validate tool usage with guardrails
                if processor and not processor.validate_tool_usage(session_id, tool_name):
                    logger.warning(f"Tool '{tool_name}' blocked by guardrails for session {session_id}")
                    tool_results_to_append.append({
                        "role": "assistant", 
                        "content": f"Attempted to use tool {tool_name}"
                    })
                    tool_results_to_append.append({
                        "role": "system", 
                        "content": f"ERROR: Tool '{tool_name}' is not allowed for this agent. Available tools: {processor.get_allowed_tools(session_id) or 'all tools allowed'}"
                    })
                    continue
                
                try:
                    tool_instance = registry.get(tool_name)

                    # Execute tool
                    if inspect.iscoroutinefunction(tool_instance.func):
                        tool_result = await tool_instance.func(**tool_args)
                    else:
                        tool_result = tool_instance.func(**tool_args)
                    
                    # Add tool call and result to be appended to messages
                    tool_results_to_append.append({
                        "role": "assistant", 
                        "content": f"Called tool {tool_name} with {tool_args}"
                    })
                    tool_results_to_append.append({
                        "role": "system", 
                        "content": f"Tool {tool_name} returned: {tool_result}"
                    })

                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {str(e)}")
                    tool_results_to_append.append({
                        "role": "system", 
                        "content": f"Error executing tool {tool_name}: {str(e)}"
                    })

            if tool_results_to_append:
                llm_messages.extend(tool_results_to_append)
                
                # Call LLM again for next iteration
                try:
                    response = await self.llm.chat(llm_messages, tools=tools, **kwargs)
                    
                    # Accumulate usage
                    loop_usage = response.get("usage", {})
                    for key in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                        total_usage[key] = total_usage.get(key, 0) + loop_usage.get(key, 0)
                    total_usage["cost"] = total_usage.get("cost", 0.0) + loop_usage.get("cost", 0.0)
                except Exception as e:
                    logger.error(f"Error in tool reasoning loop: {str(e)}")
                    break
            else:
                # No results to process, exit loop
                break

        content = response.get("content", "")

        # 5. Guardrails Output Validation
        if processor:
            content = processor.validate_output(
                content, 
                confidence=response.get("metadata", {}).get("confidence", 1.0)
            )

        # 6. Update memory if present
        if self.memory is not None:
            # Check if summarization belongs here or if it was pre-loaded
            # In the API flow, history is pre-loaded without summarization
            # Here we add the current turn which might trigger summarization
            await self.memory.add_message("user", message_content)
            await self.memory.add_message("assistant", content)

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
