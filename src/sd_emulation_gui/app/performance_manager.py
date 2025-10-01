"""
Performance Manager Module

This module provides performance optimization utilities including
lazy loading, caching, and resource management for the SD Emulation GUI.
"""

import functools
import time
import weakref
from typing import Any, Callable, Dict, Optional, TypeVar
from threading import RLock

T = TypeVar('T')


class CacheManager:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        """Initialize cache manager."""
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._ttl: Dict[str, int] = {}
        self._default_ttl = default_ttl
        self._lock = RLock()

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                return default

            # Check TTL
            if key in self._timestamps:
                ttl = self._ttl.get(key, self._default_ttl)
                if time.time() - self._timestamps[key] > ttl:
                    self._remove(key)
                    return default

            return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()
            if ttl is not None:
                self._ttl[key] = ttl

    def remove(self, key: str) -> None:
        """Remove key from cache."""
        with self._lock:
            self._remove(key)

    def _remove(self, key: str) -> None:
        """Internal remove method."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        self._ttl.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._ttl.clear()

    def size(self) -> int:
        """Get cache size."""
        return len(self._cache)

    def cleanup(self) -> int:
        """Clean up expired entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, timestamp in self._timestamps.items():
                ttl = self._ttl.get(key, self._default_ttl)
                if current_time - timestamp > ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                self._remove(key)

            return len(expired_keys)


class LazyLoader:
    """Lazy loading utility for expensive resources."""

    def __init__(self):
        """Initialize lazy loader."""
        self._factories: Dict[str, Callable] = {}
        self._loaded: Dict[str, Any] = {}
        self._loading: set = set()

    def register(self, name: str, factory: Callable[[], T]) -> None:
        """Register a lazy-loaded resource."""
        self._factories[name] = factory

    def get(self, name: str) -> T:
        """Get a lazy-loaded resource."""
        if name in self._loaded:
            return self._loaded[name]

        if name in self._loading:
            # Circular dependency or already loading
            raise RuntimeError(f"Circular dependency detected for {name}")

        if name not in self._factories:
            raise KeyError(f"No factory registered for {name}")

        self._loading.add(name)
        try:
            resource = self._factories[name]()
            self._loaded[name] = resource
            return resource
        finally:
            self._loading.remove(name)

    def preload(self, name: str) -> None:
        """Preload a resource."""
        if name not in self._loaded and name in self._factories:
            self.get(name)

    def preload_all(self) -> None:
        """Preload all registered resources."""
        for name in self._factories.keys():
            self.preload(name)

    def clear(self, name: Optional[str] = None) -> None:
        """Clear a specific resource or all resources."""
        if name:
            self._loaded.pop(name, None)
        else:
            self._loaded.clear()


class ResourceManager:
    """Manage system resources with proper cleanup."""

    def __init__(self):
        """Initialize resource manager."""
        self._resources: Dict[str, Any] = {}
        self._finalizers: Dict[str, Callable] = {}
        self._refs = []

    def register(self, name: str, resource: Any, finalizer: Optional[Callable] = None) -> None:
        """Register a resource with optional finalizer."""
        self._resources[name] = resource
        if finalizer:
            self._finalizers[name] = finalizer

    def get(self, name: str) -> Any:
        """Get a registered resource."""
        return self._resources.get(name)

    def cleanup(self, name: Optional[str] = None) -> None:
        """Clean up a specific resource or all resources."""
        names = [name] if name else list(self._resources.keys())

        for resource_name in names:
            resource = self._resources.get(resource_name)
            finalizer = self._finalizers.get(resource_name)

            if finalizer and resource:
                try:
                    finalizer(resource)
                except Exception:
                    pass  # Don't let cleanup errors break the system

            self._resources.pop(resource_name, None)
            self._finalizers.pop(resource_name, None)

    def __del__(self):
        """Cleanup all resources on destruction."""
        self.cleanup()


def cache_result(ttl: Optional[int] = None):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = "|".join(key_parts)

            # Get cache manager from global registry
            cache_mgr = get_cache_manager()
            cached_result = cache_mgr.get(cache_key)

            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_mgr.set(cache_key, result, ttl)
            return result

        return wrapper
    return decorator


def time_execution(func: Callable) -> Callable:
    """Decorator to time function execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        print(f"⚡ {func.__name__} executed in {elapsed:.3f}s".3f"        return result
    return wrapper


def memoize(func: Callable) -> Callable:
    """Simple memoization decorator."""
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create cache key
        key = str(args) + str(sorted(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper


# Global instances
_global_cache_manager = CacheManager()
_global_lazy_loader = LazyLoader()
_global_resource_manager = ResourceManager()


def get_cache_manager() -> CacheManager:
    """Get the global cache manager."""
    return _global_cache_manager


def get_lazy_loader() -> LazyLoader:
    """Get the global lazy loader."""
    return _global_lazy_loader


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager."""
    return _global_resource_manager


def cleanup_resources():
    """Clean up all global resources."""
    _global_cache_manager.clear()
    _global_lazy_loader.clear()
    _global_resource_manager.cleanup()


def preload_critical_resources():
    """Preload critical resources for better performance."""
    # This function can be customized to preload important resources
    pass
