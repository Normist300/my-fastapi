import logging
from time import perf_counter

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint


logger = logging.getLogger(__name__)


async def log_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
    started_at = perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration_ms = (perf_counter() - started_at) * 1000

        route = request.scope.get("route")
        route_path = getattr(route, "path", "<unmatched>")

        level = logging.ERROR if status_code >= 500 else logging.INFO

        logger.log(
            level,
            "method=%s route=%s status=%s duration_ms=%.2f",
            request.method,
            route_path,
            status_code,
            duration_ms,
        )