"""
Utility functions for the Skyvia MCP server.
Handles making authenticated requests to the Skyvia API.
"""

import httpx
import json
from typing import Optional, Dict, Any
from .config import get_api_key, DEFAULT_TIMEOUT, SKYVIA_BASE_URL

class SkyviaAPIError(Exception):
    """Custom exception for Skyvia API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        self.status_code = status_code
        self.details = details
        error_msg = f"Skyvia API Error: {message}"
        if status_code:
            error_msg = f"[{status_code}] {error_msg}"
        super().__init__(error_msg)

async def authenticated_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_TIMEOUT
) -> Any:
    """
    Makes an authenticated request to the Skyvia API.

    Args:
        endpoint: The API endpoint path (e.g., "/v1/workspaces").
        method: HTTP method ("GET", "POST", "PUT", "DELETE", etc.).
        params: URL query parameters.
        json_data: JSON data for the request body (for POST, PUT, etc.).
        timeout: Request timeout in seconds.

    Returns:
        The parsed JSON response from the API.

    Raises:
        SkyviaAPIError: If the API returns an error or the request fails.
        ValueError: If an unsupported HTTP method is provided.
    """
    try:
        api_key = get_api_key()
        headers = {
            "Authorization": api_key, # As per OpenAPI spec 'Access Token' security scheme
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{SKYVIA_BASE_URL}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=timeout
            )

            # Check for HTTP errors
            response.raise_for_status()

            # Attempt to parse JSON, handle empty responses for methods like DELETE
            if response.status_code == 204 or not response.content:
                 # No content to parse, return success indication or None
                 return None
            else:
                # Check if content type is JSON before parsing
                content_type = response.headers.get("content-type", "").lower()
                if "application/json" in content_type:
                    return response.json()
                else:
                    # Handle non-JSON responses if necessary, maybe return raw text
                    # Or raise an error if JSON was expected
                    raise SkyviaAPIError(
                        f"Unexpected content type received: {content_type}",
                        status_code=response.status_code,
                        details=response.text
                    )


    except httpx.HTTPStatusError as e:
        # Try to parse error details from response body
        error_details = None
        try:
            error_details = e.response.json()
            # Potentially extract a more specific message if the API provides one
            message = error_details.get("message", str(error_details))
        except (json.JSONDecodeError, AttributeError):
            message = e.response.text or f"HTTP Error {e.response.status_code}"

        raise SkyviaAPIError(
            message=message,
            status_code=e.response.status_code,
            details=error_details
        ) from e
    except httpx.RequestError as e:
        # Network errors, timeouts, etc.
        raise SkyviaAPIError(f"Request failed: {str(e)}") from e
    except ValueError as e:
         # Catch errors from get_api_key() or unsupported methods
         raise SkyviaAPIError(f"Configuration or Input Error: {str(e)}") from e
    except Exception as e:
        # Catch any other unexpected errors
        raise SkyviaAPIError(f"An unexpected error occurred: {str(e)}") from e
