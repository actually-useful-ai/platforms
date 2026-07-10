# File Purpose: Package marker for platform adapter implementations.
# Primary Functions/Classes: re-exports registry helpers.
# Inputs/Outputs: None at import time beyond adapter registration.

from platforms.adapters.registry import get_adapter, list_adapters

__all__ = ["get_adapter", "list_adapters"]
