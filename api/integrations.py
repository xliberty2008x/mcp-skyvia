"""
MCP Tools for Skyvia Integrations API endpoints.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from fastmcp import FastMCP
from .utils import authenticated_request, SkyviaAPIError

# --- Pydantic Models based on skyvia.json ---

class IntegrationDto(BaseModel):
    """Represents a Skyvia integration package."""
    id: int
    name: Optional[str] = None
    type: Optional[str] = None # e.g., "dataflow", "export", "controlflow", etc.
    created: datetime
    modified: datetime
    scheduled: bool

class IntegrationDtoHasMorePagingDto(BaseModel):
    """Paging structure for IntegrationDto list."""
    data: Optional[List[IntegrationDto]] = None
    hasMore: bool

class IntegrationExecutionLogDto(BaseModel):
    """Represents a log entry for an integration execution."""
    runId: int
    date: datetime # Note: spec shows 'date', might be start time?
    duration: int # Assuming seconds, needs confirmation
    state: str # Enum: "New", "Queued", "Running", "Succeeded", "Failed", "Canceling", "Canceled"
    successRows: int
    errorRows: int

class IntegrationExecutionLogDtoHasMorePagingDto(BaseModel):
    """Paging structure for IntegrationExecutionLogDto list."""
    data: Optional[List[IntegrationExecutionLogDto]] = None
    hasMore: bool

class IntegrationExecutionResultDto(BaseModel):
    """Represents the detailed result of a specific integration execution."""
    runId: int
    queueTime: datetime
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    state: str # Enum: "New", "Queued", "Running", "Succeeded", "Failed", "Canceling", "Canceled"
    result: Optional[str] = None # Likely contains error message on failure

class IntegrationScheduleDto(BaseModel):
    """Represents the schedule status of an integration."""
    active: bool

# --- MCP Tools ---

def register_tools(mcp: FastMCP):
    """Registers integration-related tools with the MCP server."""

    @mcp.tool()
    async def list_integrations(
        workspace_id: int = Field(..., description="The ID of the workspace containing the integrations."),
        skip: int = Field(0, description="Number of integrations to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of integrations to return (for pagination). Must be between 1 and 200.", ge=1, le=200)
    ) -> IntegrationDtoHasMorePagingDto:
        """
        Retrieves a list of integration packages within a specific workspace.

        Args:
            workspace_id: The ID of the target workspace.
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).

        Returns:
            An object containing a list of integration DTOs and a 'hasMore' flag for pagination.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/integrations"
            params = {"skip": skip, "take": take}
            response_data = await authenticated_request(endpoint=endpoint, method="GET", params=params)

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                integrations_page = IntegrationDtoHasMorePagingDto.model_validate(response_data)
                return integrations_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for integrations in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to list integrations for workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while listing integrations for workspace {workspace_id}: {str(e)}") from e

    @mcp.tool()
    async def get_integration(
        workspace_id: int = Field(..., description="The ID of the workspace containing the integration."),
        integration_id: int = Field(..., description="The ID of the integration package to retrieve.")
    ) -> IntegrationDto:
        """
        Retrieves details for a specific integration package within a workspace.

        Args:
            workspace_id: The ID of the target workspace.
            integration_id: The ID of the target integration package.

        Returns:
            An IntegrationDto object with integration package details.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., integration not found).
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/integrations/{integration_id}"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                integration_details = IntegrationDto.model_validate(response_data)
                return integration_details
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for integration {integration_id} in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get details for integration {integration_id} in workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting details for integration {integration_id} in workspace {workspace_id}: {str(e)}") from e

    # TODO: Add get_integration_executions tool based on /v1/workspaces/{workspaceId}/integrations/{integrationId}/executions (GET)
    # @mcp.tool()
    # async def get_integration_executions(...) -> IntegrationExecutionLogDtoHasMorePagingDto: ...

    @mcp.tool()
    async def run_integration(
        workspace_id: int = Field(..., description="The ID of the workspace containing the integration."),
        integration_id: int = Field(..., description="The ID of the integration package to run.")
    ) -> IntegrationExecutionLogDto:
        """
        Starts an execution run for the specified integration package.

        Args:
            workspace_id: The ID of the target workspace.
            integration_id: The ID of the target integration package to execute.

        Returns:
            An IntegrationExecutionLogDto object representing the initiated run (often shows 'Queued' or 'New' state initially).

        Raises:
            SkyviaAPIError: If the API request fails (e.g., integration not found, invalid state).
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/integrations/{integration_id}/executions"
            # POST request to trigger the execution
            response_data = await authenticated_request(endpoint=endpoint, method="POST")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic - Spec indicates it returns IntegrationExecutionLogDto
                execution_log = IntegrationExecutionLogDto.model_validate(response_data)
                return execution_log
            elif response_data is None:
                 # Handle cases where a 200/202 might be returned with no body, indicating acceptance.
                 # We might need to construct a default LogDto or raise an informative error.
                 # Let's assume for now an empty dict means something went wrong if LogDto was expected.
                 raise SkyviaAPIError(
                     message=f"Integration run for {integration_id} initiated but received no execution details.",
                     details="Empty response received"
                 )
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received when running integration {integration_id} in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to run integration {integration_id} in workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while running integration {integration_id} in workspace {workspace_id}: {str(e)}") from e

    # TODO: Add get_integration_execution_details tool based on /v1/workspaces/{workspaceId}/integrations/{integrationId}/executions/{executionId} (GET)
    # @mcp.tool()
    # async def get_integration_execution_details(...) -> IntegrationExecutionResultDto: ...

    # TODO: Add get_active_integration_execution tool based on /v1/workspaces/{workspaceId}/integrations/{integrationId}/executions/active (GET)
    # @mcp.tool()
    # async def get_active_integration_execution(...) -> IntegrationExecutionLogDto: ...

    # TODO: Add cancel_integration_execution tool based on /v1/workspaces/{workspaceId}/integrations/{integrationId}/executions/cancel (POST)
    # @mcp.tool()
    # async def cancel_integration_execution(...) -> None: ... # Expects 200 OK

    # TODO: Add kill_integration_execution tool based on /v1/workspaces/{workspaceId}/integrations/{integrationId}/executions/kill (POST)
    # @mcp.tool()
    # async def kill_integration_execution(...) -> None: ... # Expects 200 OK

    # TODO: Add get_integration_schedule tool based on /v1/workspaces/{workspaceId}/integrations/{integrationId}/schedule (GET)
    # @mcp.tool()
    # async def get_integration_schedule(...) -> IntegrationScheduleDto: ...

    # TODO: Add enable_integration_schedule tool based on /v1/workspaces/{workspaceId}/integrations/{integrationId}/schedule/enable (POST)
    # @mcp.tool()
    # async def enable_integration_schedule(...) -> IntegrationScheduleDto: ...

    # TODO: Add disable_integration_schedule tool based on /v1/workspaces/{workspaceId}/integrations/{integrationId}/schedule/disable (POST)
    # @mcp.tool()
    # async def disable_integration_schedule(...) -> IntegrationScheduleDto: ...
