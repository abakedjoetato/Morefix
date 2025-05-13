"""
Async Utilities Package

This package provides async/await compatibility helpers for different
Python and Discord library versions.
"""

from utils.async_helpers import (
    is_coroutine_function,
    ensure_async,
    ensure_sync,
    safe_gather,
    safe_wait,
    AsyncCache,
    cached_async
)

from utils.type_safety import (
    safe_cast,
    safe_str,
    safe_int,
    safe_float,
    safe_bool,
    safe_list,
    safe_dict,
    safe_function_call,
    validate_type,
    validate_func_args
)

__all__ = [
    # Async helpers
    'is_coroutine_function',
    'ensure_async',
    'ensure_sync',
    'safe_gather',
    'safe_wait',
    'AsyncCache',
    'cached_async',
    
    # Type safety
    'safe_cast',
    'safe_str',
    'safe_int',
    'safe_float',
    'safe_bool',
    'safe_list',
    'safe_dict',
    'safe_function_call',
    'validate_type',
    'validate_func_args'
]