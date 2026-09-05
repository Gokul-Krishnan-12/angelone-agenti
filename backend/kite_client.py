"""Compatibility adapter redirecting legacy kite_client references to smart_api_client."""

from .smartapi_client import (
    SmartApiClient as KiteClient,
)
from .smartapi_client import (
    convert_keys,
    kite_client,
    smart_api_client,
    to_camel,
)

__all__ = ["KiteClient", "kite_client", "smart_api_client", "to_camel", "convert_keys"]
