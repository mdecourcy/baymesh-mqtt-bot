"""
Prometheus metrics helpers.
"""

from __future__ import annotations

import os
import time

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
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
REGISTRY = CollectorRegistry()
_LAST_CPU_TIMES = None
_LAST_CPU_CHECK_TS = None

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
    registry=REGISTRY,
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
    registry=REGISTRY,
)

EXCEPTIONS = Counter(
    "http_exceptions_total",
    "Total unhandled exceptions in HTTP handlers",
    registry=REGISTRY,
)

PROCESS_CPU_PERCENT = Gauge(
    "app_process_cpu_percent",
    "Process CPU percent (psutil, averaged since last call)",
    ["pid"],
    registry=REGISTRY,
)

PROCESS_RSS_BYTES = Gauge(
    "app_process_resident_memory_bytes",
    "Process resident set size in bytes",
    ["pid"],
    registry=REGISTRY,
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
        global _LAST_CPU_TIMES, _LAST_CPU_CHECK_TS
        now = time.time()
        cpu_val = 0.0
        try:
            times = proc.cpu_times()
            if _LAST_CPU_TIMES is not None and _LAST_CPU_CHECK_TS is not None:
                delta_proc = (
                    (times.user - _LAST_CPU_TIMES.user)
                    + (times.system - _LAST_CPU_TIMES.system)
                )
                elapsed = max(now - _LAST_CPU_CHECK_TS, 1e-6)
                cpu_val = (
                    delta_proc
                    / (elapsed * max(psutil.cpu_count(logical=True) or 1, 1))
                    * 100.0
                )
            _LAST_CPU_TIMES = times
            _LAST_CPU_CHECK_TS = now
        except Exception:
            cpu_val = proc.cpu_percent(interval=0.1)

        PROCESS_CPU_PERCENT.labels(pid=PID).set(cpu_val)
        PROCESS_RSS_BYTES.labels(pid=PID).set(proc.memory_info().rss)
    except Exception:
        # Metrics collection should never crash the app
        return


def metrics_response() -> Response:
    """Return the current metrics in Prometheus exposition format."""

    update_process_metrics()
    return Response(
        content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST
    )


# Seed gauges once at import so CPU/mem metrics exist even before requests
update_process_metrics()
