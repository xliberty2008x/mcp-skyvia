"""
Configuration module for the Skyvia MCP server.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# --- Skyvia API Configuration ---
SKYVIA_BASE_URL = "https://api.skyvia.com" # Base URL for Skyvia API v1
API_TOKEN_ENV_VAR = "SKYVIA_API_TOKEN"    # Environment variable name for the token

# --- Server Metadata ---
SERVER_NAME = "Skyvia MCP Server"
SERVER_DESCRIPTION = "MCP Server for interacting with the Skyvia API"
SERVER_VERSION = "0.1.0"
# fastmcp should be implicitly included by the library itself
SERVER_DEPENDENCIES = ["httpx", "python-dotenv"]

# --- Internal State ---
# Store the token globally within this module after it's first retrieved or set.
# Be cautious with global state in web servers; might need refinement if concurrency issues arise.
_api_token: Optional[str] = None

def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Gets an environment variable."""
    return os.environ.get(key, default)

def set_api_key(token: str):
    """Sets the API key for the current session."""
    global _api_token
    if not token or not isinstance(token, str):
        raise ValueError("Invalid API token provided.")
    _api_token = token

def get_api_key() -> str:
    """
    Gets the Skyvia API key.
    It prioritizes the token set via `set_api_key` (e.g., from CLI arg),
    then checks the environment variable, then raises an error.
    """
    global _api_token
    if _api_token:
        return _api_token

    # If not set via CLI, try environment variable
    token_from_env = get_env(API_TOKEN_ENV_VAR)
    if token_from_env:
        _api_token = token_from_env
        return _api_token

    # If still not found, raise an error
    raise ValueError(
        f"Skyvia API token not found. Please set the '{API_TOKEN_ENV_VAR}' "
        "environment variable or provide it using the --skyvia-api-token argument."
    )

# --- Request Configuration ---
DEFAULT_TIMEOUT = 30.0  # Default timeout for API requests in seconds
