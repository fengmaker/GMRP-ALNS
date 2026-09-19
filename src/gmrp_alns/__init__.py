"""GMRP-ALNS: reproducible machine reassignment research tools."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gmrp-alns")
except PackageNotFoundError:  # pragma: no cover - source tree without installation
    __version__ = "1.0.0"

__all__ = ["__version__"]
