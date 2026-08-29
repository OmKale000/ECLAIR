"""Shared exception types for ECLAIR (M01 Foundation).

Every module (M02-M18) MUST reuse these exception types rather than inventing a
new error format (COMMON_RULES sec.11). This module defines the shared hierarchy
only; it implements no reliability behaviour.

Hierarchy::

    EclairError                     (base for all ECLAIR errors)
     |- ConfigurationError          (invalid/missing configuration)
     |- ContractValidationError     (a shared contract failed validation)
     |- ModuleError                 (base for module-level failures)

`EclairError` carries an optional machine-readable ``code`` so downstream
layers (API/SDK) can surface a stable error format without re-inventing one.
"""

from __future__ import annotations

__all__ = [
    "EclairError",
    "ConfigurationError",
    "ContractValidationError",
    "ModuleError",
]


class EclairError(Exception):
    """Base class for all ECLAIR errors.

    Args:
        message: Human-readable description of the error.
        code: Optional stable, machine-readable error code.
    """

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class ConfigurationError(EclairError):
    """Raised when application configuration is missing or invalid."""


class ContractValidationError(EclairError):
    """Raised when data does not conform to a shared contract."""


class ModuleError(EclairError):
    """Base class for failures raised by individual reliability modules."""
