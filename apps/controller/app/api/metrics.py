import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response

router = APIRouter()

# Metrics
REQUEST_COUNT = Counter(
    'aidp_controller_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'aidp_controller_request_latency_seconds',
    'Request latency',
    ['method', 'endpoint']
)

TOOL_INVOCATIONS = Counter(
    'aidp_controller_tool_invocations_total',
    'Total tool invocations',
    ['tool_name', 'capability', 'status']
)

TOOL_LATENCY = Histogram(
    'aidp_controller_tool_invocation_latency_seconds',
    'Tool invocation latency',
    ['tool_name', 'capability']
)

ACTIVE_TOOLS = Gauge(
    'aidp_controller_active_tools',
    'Number of registered tools'
)

HEALTHY_TOOLS = Gauge(
    'aidp_controller_healthy_tools',
    'Number of healthy tools'
)


def record_request(method: str, endpoint: str, status: int, latency: float):
    """Record HTTP request metrics."""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)


def record_tool_invocation(tool_name: str, capability: str, status: str, latency: float):
    """Record tool invocation metrics."""
    TOOL_INVOCATIONS.labels(tool_name=tool_name, capability=capability, status=status).inc()
    TOOL_LATENCY.labels(tool_name=tool_name, capability=capability).observe(latency)


def update_tool_counts(active: int, healthy: int):
    """Update tool count gauges."""
    ACTIVE_TOOLS.set(active)
    HEALTHY_TOOLS.set(healthy)


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
