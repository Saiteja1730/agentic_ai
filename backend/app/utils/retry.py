"""Retry helper for flaky external API calls."""
import asyncio
import functools
from typing import Any, Callable, TypeVar

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def async_retry(max_attempts: int = 3, base_delay: float = 1.0, exceptions: tuple = (Exception,)):
    """Decorator that retries an async function with exponential backoff."""

    def decorator(func: Callable[..., "asyncio.Future[T]"]) -> Callable[..., "asyncio.Future[T]"]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001
                    last_exc = exc
                    logger.warning(
                        "Attempt %s/%s failed for %s: %s", attempt, max_attempts, func.__name__, exc
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator
