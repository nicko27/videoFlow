"""
Timeout utilities for preventing infinite blocking operations.

Provides context managers and decorators for adding timeouts to operations.
"""

import signal
import threading
from contextlib import contextmanager
from typing import Optional
from src.core.logger import Logger

logger = Logger.get_logger('DuplicateFinder.Timeout')


class TimeoutError(Exception):
    """Raised when an operation times out."""
    pass


@contextmanager
def timeout(seconds: int, operation_name: str = "Operation"):
    """
    Context manager pour ajouter un timeout à n'importe quelle opération.

    Usage:
        with timeout(60, "Video processing"):
            result = process_video(path)

    Args:
        seconds: Timeout en secondes
        operation_name: Nom de l'opération (pour logging)

    Raises:
        TimeoutError: Si l'opération dépasse le timeout
    """
    if seconds <= 0:
        yield
        return

    def timeout_handler(signum, frame):
        raise TimeoutError(f"{operation_name} timed out after {seconds}s")

    # Unix: utiliser SIGALRM
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Windows fallback: utiliser threading.Timer
        # Note: Ne peut pas interrompre une opération bloquante
        # mais peut au moins détecter le timeout
        timer_triggered = threading.Event()

        def timer_callback():
            timer_triggered.set()
            logger.warning(f"⏰ {operation_name} exceeded {seconds}s timeout")

        timer = threading.Timer(seconds, timer_callback)
        timer.daemon = True
        timer.start()

        try:
            yield
        finally:
            timer.cancel()
            if timer_triggered.is_set():
                raise TimeoutError(f"{operation_name} timed out after {seconds}s")


def timeout_decorator(seconds: int, operation_name: Optional[str] = None):
    """
    Decorator pour ajouter un timeout à une fonction.

    Usage:
        @timeout_decorator(60, "Video hashing")
        def hash_video(path):
            return compute_hash(path)

    Args:
        seconds: Timeout en secondes
        operation_name: Nom de l'opération (utilise le nom de la fonction si None)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__name__}()"
            with timeout(seconds, name):
                return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator
