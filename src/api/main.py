"""
FastAPI application entrypoint.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src import metrics
from src.exceptions import (
    DatabaseError,
    MeshtasticCommandError,
    MessageParsingError,
    MQTTConnectionError,
    StatisticsError,
    SubscriptionError,
)
from src.logger import get_logger
from src.schemas import ErrorResponse

from .routes import router


app = FastAPI(
    title="Meshtastic Statistics Bot API",
    description=(
        "REST endpoints for monitoring and testing "
        "Meshtastic mesh statistics."
    ),
    version="0.1.0",
)

logger = get_logger("api.main")

# Global state for health checks
app.state.mqtt_client = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next: Callable):
    """
    Attach request ID and log request/response lifecycle.
    """

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start_time = time.time()
    logger.info("REQ %s %s %s", request_id, request.method, request.url.path)
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        metrics.record_exception()
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        duration_s = duration_ms / 1000
        path_template = request.url.path
        route = request.scope.get("route")
        if route and getattr(route, "path", None):
            path_template = route.path
        metrics.record_request(
            request.method, path_template, status_code, duration_s
        )
        metrics.update_process_metrics()
        if "response" in locals():
            response.headers["X-Request-ID"] = request_id
        logger.info(
            "RES %s %s %s %.2fms",
            request_id,
            status_code,
            path_template,
            duration_ms,
        )


@app.get("/metrics")
async def metrics_endpoint() -> Response:
    return metrics.metrics_response()


def _error_response(status_code: int, error: str, detail: str) -> JSONResponse:
    payload = ErrorResponse(
        error=error, detail=detail, status_code=status_code
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@app.exception_handler(SubscriptionError)
async def subscription_error_handler(
    _: Request, exc: SubscriptionError
) -> JSONResponse:
    logger.error("Subscription error: %s", exc, exc_info=True)
    return _error_response(400, "subscription_error", str(exc))


@app.exception_handler(StatisticsError)
async def statistics_error_handler(
    _: Request, exc: StatisticsError
) -> JSONResponse:
    logger.error("Statistics error: %s", exc, exc_info=True)
    return _error_response(500, "statistics_error", str(exc))


@app.exception_handler(DatabaseError)
async def database_error_handler(
    _: Request, exc: DatabaseError
) -> JSONResponse:
    logger.error("Database error: %s", exc, exc_info=True)
    return _error_response(500, "database_error", str(exc))


@app.exception_handler(MeshtasticCommandError)
async def meshtastic_error_handler(
    _: Request, exc: MeshtasticCommandError
) -> JSONResponse:
    logger.error("Meshtastic command error: %s", exc, exc_info=True)
    return _error_response(502, "meshtastic_error", str(exc))


@app.exception_handler(MQTTConnectionError)
async def mqtt_error_handler(
    _: Request, exc: MQTTConnectionError
) -> JSONResponse:
    logger.error("MQTT connection error: %s", exc, exc_info=True)
    return _error_response(503, "mqtt_error", str(exc))


@app.exception_handler(MessageParsingError)
async def parsing_error_handler(
    _: Request, exc: MessageParsingError
) -> JSONResponse:
    logger.error("Message parsing error: %s", exc, exc_info=True)
    return _error_response(400, "message_parsing_error", str(exc))


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    _: Request, exc: Exception
) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return _error_response(
        500, "internal_error", "An unexpected error occurred."
    )


app.include_router(router)

# Serve the dashboard static files (must be last, as it catches all routes)
dashboard_dist = Path(__file__).parent.parent.parent / "dashboard" / "dist"
if dashboard_dist.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(dashboard_dist), html=True),
        name="dashboard",
    )
    logger.info("Serving dashboard from %s", dashboard_dist)
else:
    logger.warning("Dashboard dist directory not found at %s", dashboard_dist)
