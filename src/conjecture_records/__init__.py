"""Source-bound conjecture records."""

from .schema import SCHEMA_VERSION, validate_catalog, validate_record

__all__ = ["SCHEMA_VERSION", "validate_catalog", "validate_record"]
__version__ = "0.1.0"
