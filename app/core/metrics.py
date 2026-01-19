"""Prometheus metrics configuration for the application."""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest
from fastapi import Response

# Create a custom registry
registry = CollectorRegistry()

# Define common metrics
REQUEST_COUNT = Counter(
    "http_requests_total", 
    "Total number of HTTP requests", 
    ["method", "endpoint", "status"],
    registry=registry
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", 
    "HTTP request latency in seconds", 
    ["method", "endpoint"],
    registry=registry
)

AGENT_EXECUTION_COUNT = Counter(
    "agent_execution_total",
    "Total number of agent executions",
    ["agent_name", "status"],
    registry=registry
)

TOKEN_USAGE = Counter(
    "llm_token_usage_total",
    "Total tokens used by LLM",
    ["agent_name", "model", "token_type"], # token_type can be 'prompt', 'completion'
    registry=registry
)

CHAT_COST = Counter(
    "llm_chat_cost_total",
    "Total estimated cost for LLM calls",
    ["agent_name", "model"],
    registry=registry
)

def get_metrics_report() -> Response:
    """Generate Prometheus metrics report."""
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
