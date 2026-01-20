"""
Utility functions and decorators for the library.

This module contains helpers for logging and argument validation.
"""

import inspect
import logging
from functools import wraps
from types import FunctionType
from typing import Any, Callable, TypeVar

from pydantic import ConfigDict, validate_call

configured_validate_call = validate_call(config = ConfigDict(arbitrary_types_allowed=True))

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _safe_repr(obj: Any, limit=100) -> str:
    """
    Returns a safe string representation of an object, truncating it if necessary.
    """
    if isinstance(obj, bytes):
        return f"<bytes object of length {len(obj)}>"

    try:
        obj_repr = repr(obj)
    except Exception:
        return f"<unrepresentable object of type {type(obj).__name__}>"

    if len(obj_repr) > limit:
        obj_repr = obj_repr[:limit] + "..."

    return obj_repr


def _gen_args_str(args: list, kwargs: dict) -> str:
    """
    Generates a string representation of arguments and keyword arguments for logging.
    """
    positional_args = [_safe_repr(arg) for arg in args]
    keyword_args = [f"{k} = {_safe_repr(v)}" for k, v in kwargs.items()]

    return ", ".join(positional_args + keyword_args)


def log_call(func: Callable) -> Callable:
    """
    Decorator that logs the start and end of a synchronous function call.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(
            f"Function {func.__qualname__} started with args: {_gen_args_str(args, kwargs)}.")
        result = func(*args, **kwargs)
        logger.debug(f"Function {func.__qualname__} finished.")
        return result

    return wrapper


def log_async_call(func: Callable) -> Callable:
    """
    Decorator that logs the start and end of an asynchronous function call.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.debug(
            f"Function {func.__qualname__} started with args: {_gen_args_str(args, kwargs)}.")
        result = await func(*args, **kwargs)
        logger.debug(f"Function {func.__qualname__} finished.")
        return result

    return wrapper


def log_async_gen_call(func: Callable) -> Callable:
    """
    Decorator that logs the start and end of an asynchronous generator call.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.debug(
            f"Function {func.__qualname__} started with args: {_gen_args_str(args, kwargs)}.")
        result = func(*args, **kwargs)
        async for obj in result:
            yield obj
        logger.debug(f"Function {func.__qualname__} finished.")

    return wrapper

T = TypeVar('T', bound=type)

def log_class(cls: T) -> T:
    """
    Class decorator that applies logging to all public methods.

    It automatically detects synchronous functions, coroutines, and async generators,
    applying the appropriate logging decorator to each.
    """
    for attr_name, attr_value in cls.__dict__.items():
        if isinstance(attr_value, FunctionType) and not attr_name.startswith("__"):
            if inspect.iscoroutinefunction(attr_value):
                new_func = log_async_call(attr_value)
            elif inspect.isasyncgenfunction(attr_value):
                new_func = log_async_gen_call(attr_value)
            else:
                new_func = log_call(attr_value)
            setattr(cls, attr_name, new_func)
    return cls

__all__ = ["configured_validate_call", "log_call", "log_async_call", "log_async_gen_call", "log_class"]