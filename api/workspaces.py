"""
MCP Tools for Skyvia Workspaces API endpoints.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from .utils import authenticated_request, SkyviaAPIError

# --- Pydantic Models based on skyvia.json ---

class WorkspaceDto(BaseModel):
    """Represents a Skyvia workspace."""
    id: int
    name: Optional[str] = None
    isPersonal: bool

# --- MCP Tools ---

def register_tools(mcp: FastMCP):
    """Registers workspace-related tools with the MCP server."""

    @mcp.tool()
    async def list_workspaces() -> List[WorkspaceDto]:
        """
        Retrieves a list of all workspaces available to the user account.

        Returns:
            A list of workspace objects containing id, name, and isPersonal flag.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            response_data = await authenticated_request(endpoint="/v1/workspaces", method="GET")
            # The response is directly a list of WorkspaceDto objects according to the spec
            if isinstance(response_data, list):
                # Validate data using Pydantic
                workspaces = [WorkspaceDto.model_validate(item) for item in response_data]
                return workspaces
            else:
                # Should not happen based on spec, but handle unexpected format
                raise SkyviaAPIError(
                    message=f"Unexpected response format received: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            # Re-raise the specific error for clarity
            raise e
        except Exception as e:
            # Catch any other unexpected errors during processing
            raise SkyviaAPIError(f"An unexpected error occurred while listing workspaces: {str(e)}") from e

    @mcp.tool()
    async def get_workspace(workspace_id: int = Field(..., description="The unique identifier for the workspace.")) -> WorkspaceDto:
        """
        Retrieves details for a specific workspace.

        Args:
            workspace_id: The ID of the workspace to retrieve.

        Returns:
            A workspace object containing id, name, and isPersonal flag.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., workspace not found).
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")
            if isinstance(response_data, dict):
                # Validate data using Pydantic
                workspace = WorkspaceDto.model_validate(response_data)
                return workspace
            else:
                 # Should not happen based on spec for a single item, but handle unexpected format
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
             # Add context to the error message
             raise SkyviaAPIError(f"Failed to get workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            # Catch any other unexpected errors
            raise SkyviaAPIError(f"An unexpected error occurred while getting workspace {workspace_id}: {str(e)}") from e


    # TODO: Add tools for workspace users if needed
    # /v1/workspaces/{workspaceId}/users (GET, POST, DELETE)
