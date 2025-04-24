"""
MCP Tools for Skyvia Connections API endpoints.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from .utils import authenticated_request, SkyviaAPIError

# --- Pydantic Models based on skyvia.json ---

class ConnectionDto(BaseModel):
    """Represents a basic Skyvia connection."""
    id: int
    name: Optional[str] = None
    connector: Optional[str] = None

class ConnectionDtoHasMorePagingDto(BaseModel):
    """Paging structure for ConnectionDto list."""
    data: Optional[List[ConnectionDto]] = None
    hasMore: bool

class ConnectionDetailsDto(BaseModel):
    """Represents detailed Skyvia connection information."""
    # Duplicating fields from ConnectionDto as inheritance with Pydantic can be tricky sometimes,
    # especially with optional fields. Explicit definition is safer.
    id: int
    name: Optional[str] = None
    connector: Optional[str] = None
    type: str # Enum: "Direct", "Agent"

class ApiResult(BaseModel):
    """Represents a generic API result message, often used for test operations."""
    message: Optional[str] = None
    refresh: bool = False # Default based on observing the spec, might need adjustment

# --- MCP Tools ---

def register_tools(mcp: FastMCP):
    """Registers connection-related tools with the MCP server."""

    @mcp.tool()
    async def list_connections(
        workspace_id: int = Field(..., description="The ID of the workspace containing the connections."),
        skip: int = Field(0, description="Number of connections to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of connections to return (for pagination). Must be between 1 and 200.", ge=1, le=200)
    ) -> ConnectionDtoHasMorePagingDto:
        """
        Retrieves a list of connections within a specific workspace.

        Args:
            workspace_id: The ID of the target workspace.
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).

        Returns:
            An object containing a list of connection DTOs and a 'hasMore' flag for pagination.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/connections"
            params = {"skip": skip, "take": take}
            response_data = await authenticated_request(endpoint=endpoint, method="GET", params=params)

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                connections_page = ConnectionDtoHasMorePagingDto.model_validate(response_data)
                return connections_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for connections in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to list connections for workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while listing connections for workspace {workspace_id}: {str(e)}") from e

    @mcp.tool()
    async def get_connection_details(
        workspace_id: int = Field(..., description="The ID of the workspace containing the connection."),
        connection_id: int = Field(..., description="The ID of the connection to retrieve details for.")
    ) -> ConnectionDetailsDto:
        """
        Retrieves detailed information for a specific connection within a workspace.

        Args:
            workspace_id: The ID of the target workspace.
            connection_id: The ID of the target connection.

        Returns:
            A ConnectionDetailsDto object with detailed connection information.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., connection not found).
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/connections/{connection_id}"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                connection_details = ConnectionDetailsDto.model_validate(response_data)
                return connection_details
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for connection {connection_id} in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get details for connection {connection_id} in workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting details for connection {connection_id} in workspace {workspace_id}: {str(e)}") from e

    @mcp.tool()
    async def test_connection(
        workspace_id: int = Field(..., description="The ID of the workspace containing the connection."),
        connection_id: int = Field(..., description="The ID of the connection to test.")
    ) -> ApiResult:
        """
        Tests the specified connection within a workspace.

        Args:
            workspace_id: The ID of the target workspace.
            connection_id: The ID of the target connection to test.

        Returns:
            An ApiResult object, typically containing a success or failure message.

        Raises:
            SkyviaAPIError: If the API request fails or the test itself indicates an error.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/connections/{connection_id}/test"
            # Test connection is a POST request according to the spec
            response_data = await authenticated_request(endpoint=endpoint, method="POST")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                result = ApiResult.model_validate(response_data)
                # Check if the API indicates failure within the message itself, although
                # usually HTTP status codes handle explicit errors. This adds a layer.
                if "error" in (result.message or "").lower() or "fail" in (result.message or "").lower():
                     raise SkyviaAPIError(message=f"Connection test failed: {result.message}", details=result)
                return result
            elif response_data is None:
                 # Handle cases where a 2xx status might be returned with no body, indicating success.
                 # Adjust based on observed API behavior if necessary.
                 return ApiResult(message="Connection test initiated successfully (No content returned).", refresh=False)
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for testing connection {connection_id} in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            # Modify error message if it's a 4xx/5xx indicating the test *call* failed, vs test *result* failed
            if e.status_code and e.status_code >= 400:
                 raise SkyviaAPIError(f"Failed to initiate test for connection {connection_id}: {e}", status_code=e.status_code, details=e.details) from e
            else: # May already be a failure message from the logic above
                 raise e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while testing connection {connection_id} in workspace {workspace_id}: {str(e)}") from e
