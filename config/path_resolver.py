"""Compatibility layer required by the test-suite.

This module re-exports the implementation under ``meta.config.path_resolver``
while keeping a singleton cache that tests can patch easily.
"""

from __future__ import annotations

import sys
from typing import Callable

from meta.config import path_resolver as _impl

PathResolutionResult = _impl.PathResolutionResult
PathResolutionStrategy = _impl.PathResolutionStrategy
PathResolver = _impl.PathResolver
PathConfigManager = _impl.PathConfigManager  # type: ignore[attr-defined]

_path_resolver: PathResolver | None = None


def _module() -> object:
    return sys.modules[__name__]


def _get_resolver_class() -> type:
    module = _module()
    resolver_cls = getattr(module, "PathResolver", None)
    if resolver_cls is not None:
        return resolver_cls
    return PathResolver


def get_path_resolver(config_manager: PathConfigManager | None = None) -> PathResolver:
    global _path_resolver
    resolver_cls = getattr(_module(), "PathResolver", PathResolver)

    if config_manager is not None:
        return resolver_cls(config_manager=config_manager)

    if _path_resolver is None:
        _path_resolver = resolver_cls(config_manager=config_manager)
    return _path_resolver


def _get_resolver_getter() -> Callable[..., PathResolver]:
    module = _module()
    getter = getattr(module, "get_path_resolver", None)
    if getter is not None:
        return getter
    return get_path_resolver


def resolve_path(
    path_input: str | _impl.Path,
    strategy: PathResolutionStrategy = PathResolutionStrategy.AUTO,
    *,
    config_manager: PathConfigManager | None = None,
) -> PathResolutionResult:
    resolver_getter = _get_resolver_getter()
    resolver = resolver_getter(config_manager=config_manager)
    return resolver.resolve_path(path_input, strategy)


def convert_hardcoded_path(
    hardcoded_path: str,
    *,
    config_manager: PathConfigManager | None = None,
) -> str:
    resolver_getter = _get_resolver_getter()
    resolver = resolver_getter(config_manager=config_manager)
    return resolver.convert_hardcoded_path(hardcoded_path)


__all__ = [
    "PathResolver",
    "PathResolutionResult",
    "PathResolutionStrategy",
    "convert_hardcoded_path",
    "get_path_resolver",
    "resolve_path",
]