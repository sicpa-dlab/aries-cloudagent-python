"""Routes for NGI Plugin."""
import prometheus_client
from aiohttp import web
from aiohttp_apispec import docs, response_schema

from prometheus_client import make_wsgi_app, Counter, Histogram

REQUEST_COUNT = Counter(
    'request_count', 'App Request Count',
    ['app_name', 'method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency',
                            ['app_name', 'endpoint']
                            )


@docs(
    tags=["Mertrics"],
    summary="Metrics management",
)
async def metrics_def(request: web.BaseRequest):
    """
    Request handler for sending a request invitation to a connection.
    Args:
        request: aiohttp request object
    """

    metrics = prometheus_client.generate_latest()
    return web.json_response({"hello": "world"})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [web.get("/metrics", metrics_def)]
    )
