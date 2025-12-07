"""
Prometheus metrics helpers.
"""

from __future__ import annotations

import os

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None  # type: ignore

PID = os.getpid()

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2,
        5,
        10,
    ),
)

EXCEPTIONS = Counter(
    "http_exceptions_total", "Total unhandled exceptions in HTTP handlers"
)

PROCESS_CPU_PERCENT = Gauge(
    "process_cpu_percent",
    "Process CPU percent (psutil, averaged since last call)",
    ["pid"],
)

PROCESS_RSS_BYTES = Gauge(
    "process_resident_memory_bytes",
    "Process resident set size in bytes",
    ["pid"],
)


def _safe_path(path: str) -> str:
    """
    Avoid high-cardinality labels by trimming query strings.
    """

    return path.split("?", 1)[0]


def record_request(
    method: str, path: str, status: int, duration_seconds: float
) -> None:
    """Record request counters and latency histogram."""

    label_path = _safe_path(path)
    status_str = str(status)
    REQUESTS.labels(method=method, path=label_path, status=status_str).inc()
    REQUEST_DURATION.labels(
        method=method, path=label_path, status=status_str
    ).observe(duration_seconds)


def record_exception() -> None:
    """Increment exception counter."""

    EXCEPTIONS.inc()


def update_process_metrics() -> None:
    """Refresh CPU and memory gauges."""

    if psutil is None:
        return
    try:
        proc = psutil.Process(PID)
        PROCESS_CPU_PERCENT.labels(pid=PID).set(proc.cpu_percent())
        PROCESS_RSS_BYTES.labels(pid=PID).set(proc.memory_info().rss)
    except Exception:
        # Metrics collection should never crash the app
        return


def metrics_response() -> Response:
    """Return the current metrics in Prometheus exposition format."""

    update_process_metrics()
    return Response(
        content=generate_latest(), media_type=CONTENT_TYPE_LATEST
    )
