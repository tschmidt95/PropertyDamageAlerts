"""
Property Damage Alerts – Florida disaster monitoring & Public Adjuster marketing system.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("property-damage-alerts")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = ["__version__"]
