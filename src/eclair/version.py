"""ECLAIR project version metadata (M01 Foundation).

Single source of truth for the project version. Imported wherever a version
string is needed. No behaviour beyond exposing the constant.
"""

from __future__ import annotations

__all__ = ["__version__", "VERSION"]

__version__: str = "0.1.0"
VERSION: str = __version__
