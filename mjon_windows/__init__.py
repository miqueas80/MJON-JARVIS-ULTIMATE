"""MJON AI OS Windows edition: portable backend without a new visual shell.

All changes to the approved Windows UI remain outside this package.
No auto-installs, background tasks or cloud calls on import.
"""
from .backend import (
    StorageBudget, diagnose_windows, inspect_windows_catalog, local_chat,
    model_directory, ollama_model_directory, plan_windows_capability, storage_budget, windows_settings,
)

__all__ = [
    "StorageBudget", "diagnose_windows", "inspect_windows_catalog", "local_chat",
    "model_directory", "ollama_model_directory", "plan_windows_capability", "storage_budget", "windows_settings",
]
