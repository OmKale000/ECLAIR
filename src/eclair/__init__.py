"""ECLAIR — Foundation package (M01).

Exposes the shared version constant, configuration mechanism, and exception
types. Shared contracts live in :mod:`eclair.contracts`.
"""

from __future__ import annotations

from eclair.config import EclairConfig, load_config
from eclair.exceptions import (
    ConfigurationError,
    ContractValidationError,
    EclairError,
    ModuleError,
)
from eclair.version import VERSION, __version__

__all__ = [
    "__version__",
    "VERSION",
    "EclairConfig",
    "load_config",
    "EclairError",
    "ConfigurationError",
    "ContractValidationError",
    "ModuleError",
]
