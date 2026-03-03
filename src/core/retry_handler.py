"""Gold Tier error recovery — @with_retry decorator and ErrorCategory enum."""
from __future__ import annotations

import functools
import logging
import random
import time
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ErrorCategory(Enum):
    """Classification of errors for retry and degradation decisions."""
    TRANSIENT = "transient"   # network timeout, 429 — retry allowed
    AUTH = "auth"             # 401/403 — no retry; alert + pause watcher
    LOGIC = "logic"           # unexpected response — quarantine item
    DATA = "data"             # parse error — quarantine item
    SYSTEM = "system"         # process crash — watchdog handles


_NO_RETRY_CATEGORIES = {ErrorCategory.AUTH, ErrorCategory.LOGIC, ErrorCategory.DATA}


def _compute_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """Exponential back-off with uniform jitter."""
    exp_delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, 0.5)
    return max(0.0, exp_delay + jitter)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> Callable[[F], F]:
    """Decorator: retry on transient failures with exponential back-off.

    AUTH, LOGIC, DATA category errors are NOT retried.
    TRANSIENT errors (and unmarked exceptions) are retried up to max_attempts.

    Usage:
        @with_retry(max_attempts=3, base_delay=1.0, max_delay=60.0)
        def call_external_api(...):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    category = getattr(exc, "error_category", None)
                    if category in _NO_RETRY_CATEGORIES:
                        raise
                    last_exc = exc
                    if attempt < max_attempts - 1:
                        delay = _compute_delay(attempt, base_delay, max_delay)
                        logger.warning(
                            "Retry %d/%d for %s after %.2fs — %s: %s",
                            attempt + 1,
                            max_attempts - 1,
                            func.__name__,
                            delay,
                            type(exc).__name__,
                            exc,
                        )
                        time.sleep(delay)
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator


def categorise_http_error(status_code: int) -> ErrorCategory:
    """Map HTTP status code to ErrorCategory."""
    if status_code in (401, 403):
        return ErrorCategory.AUTH
    if status_code == 429:
        return ErrorCategory.TRANSIENT
    if 500 <= status_code < 600:
        return ErrorCategory.TRANSIENT
    if 400 <= status_code < 500:
        return ErrorCategory.LOGIC
    return ErrorCategory.SYSTEM
