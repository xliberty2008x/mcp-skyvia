"""
MCP Tools for Skyvia Automations API endpoints.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from .utils import authenticated_request, SkyviaAPIError

# --- Pydantic Models based on skyvia.json ---

class AutomationDto(BaseModel):
    """Represents a Skyvia automation."""
    id: int
    name: Optional[str] = None
    triggerType: str # Enum: "Manual", "Schedule", "Connection", "Webhook"
    created: datetime
    modified: datetime

class AutomationDtoHasMorePagingDto(BaseModel):
    """Paging structure for AutomationDto list."""
    data: Optional[List[AutomationDto]] = None
    hasMore: bool

class AutomationLogItemDto(BaseModel):
    """Represents a log entry for an automation execution."""
    executionId: int # Note: Spec says int64, Python int handles large integers
    state: str # Enum: "Executing", "Succeeded", "Failed", "Canceling", "Canceled", "Killing"
    date: datetime
    billedTasks: int # Note: Spec says int64
    testMode: bool

class AutomationLogItemDtoHasMorePagingDto(BaseModel):
    """Paging structure for AutomationLogItemDto list."""
    data: Optional[List[AutomationLogItemDto]] = None
    hasMore: bool

class AutomationLogItemDetailsDto(BaseModel):
    """Detailed log information for an automation execution."""
    executionId: int # int64
    state: str # Enum from AutomationLogItemDto
    version: int
    testMode: bool
    comment: Optional[str] = None
    started: datetime
    executed: Optional[datetime] = None
    billedTasks: Optional[int] = None # int32
    error: Optional[str] = None

class AutomationExecutionStateDto(BaseModel):
    """Represents the state of an actively running automation."""
    executionId: int # int64
    date: datetime
    state: Optional[str] = None # Running state?
    testMode: bool

class AutomationQueueStateDto(BaseModel):
    """State of the automation queue."""
    queuedCount: int

class AutomationTriggerStateDto(BaseModel):
    """State of the automation trigger."""
    enabled: bool

class AutomationStateDto(BaseModel):
    """Overall state of an automation."""
    trigger: Optional[AutomationTriggerStateDto] = None # Made optional as structure might vary
    queue: Optional[AutomationQueueStateDto] = None
    executing: Optional[AutomationExecutionStateDto] = None
    testMode: Optional[bool] = None

# --- MCP Tools ---

def register_tools(mcp: FastMCP):
    """Registers automation-related tools with the MCP server."""

    @mcp.tool()
    async def list_automations(
        workspace_id: int = Field(..., description="The ID of the workspace containing the automations."),
        skip: int = Field(0, description="Number of automations to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of automations to return (for pagination). Must be between 1 and 200.", ge=1, le=200)
    ) -> AutomationDtoHasMorePagingDto:
        """
        Retrieves a list of automations within a specific workspace.

        Args:
            workspace_id: The ID of the target workspace.
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).

        Returns:
            An object containing a list of automation DTOs and a 'hasMore' flag for pagination.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/automations"
            params = {"skip": skip, "take": take}
            response_data = await authenticated_request(endpoint=endpoint, method="GET", params=params)

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                automations_page = AutomationDtoHasMorePagingDto.model_validate(response_data)
                return automations_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for automations in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to list automations for workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while listing automations for workspace {workspace_id}: {str(e)}") from e

    @mcp.tool()
    async def get_automation(
        workspace_id: int = Field(..., description="The ID of the workspace containing the automation."),
        automation_id: int = Field(..., description="The ID of the automation to retrieve.")
    ) -> AutomationDto:
        """
        Retrieves details for a specific automation within a workspace.

        Args:
            workspace_id: The ID of the target workspace.
            automation_id: The ID of the target automation.

        Returns:
            An AutomationDto object with automation details.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., automation not found).
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/automations/{automation_id}"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                automation_details = AutomationDto.model_validate(response_data)
                return automation_details
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for automation {automation_id} in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get details for automation {automation_id} in workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting details for automation {automation_id} in workspace {workspace_id}: {str(e)}") from e

    @mcp.tool()
    async def get_automation_executions(
        workspace_id: int = Field(..., description="The ID of the workspace containing the automation."),
        automation_id: int = Field(..., description="The ID of the automation whose executions are to be retrieved."),
        start_date: Optional[datetime] = Field(None, description="Filter executions started after this date/time."),
        end_date: Optional[datetime] = Field(None, description="Filter executions started before this date/time."),
        failed: Optional[bool] = Field(None, description="Filter only failed executions (true) or non-failed ones (false)."),
        skip: int = Field(0, description="Number of executions to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of executions to return (for pagination). Must be between 1 and 200.", ge=1, le=200),
        sort_order: str = Field("asc", description="Sort order: 'asc' (ascending) or 'desc' (descending).", pattern="^(asc|desc)$"),
        sort_by: str = Field("date", description="Field to sort by: 'date' or 'executionId'.", pattern="^(date|executionId)$")
    ) -> AutomationLogItemDtoHasMorePagingDto:
        """
        Retrieves the finished execution history for a specific automation.

        Args:
            workspace_id: The ID of the target workspace.
            automation_id: The ID of the target automation.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            failed: Optional filter for failed status.
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).
            sort_order: Sort order ('asc' or 'desc', default 'asc').
            sort_by: Field to sort by ('date' or 'executionId', default 'date').

        Returns:
            An object containing a list of automation execution log DTOs and a 'hasMore' flag.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/automations/{automation_id}/executions"
            params = {
                "skip": skip,
                "take": take,
                "sortOrder": sort_order,
                "sortBy": sort_by,
            }
            if start_date:
                params["startDate"] = start_date.isoformat()
            if end_date:
                params["endDate"] = end_date.isoformat()
            if failed is not None:
                params["failed"] = failed

            # Remove None values from params before sending
            params = {k: v for k, v in params.items() if v is not None}

            response_data = await authenticated_request(endpoint=endpoint, method="GET", params=params)

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                executions_page = AutomationLogItemDtoHasMorePagingDto.model_validate(response_data)
                return executions_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for executions of automation {automation_id} in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get executions for automation {automation_id} in workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting executions for automation {automation_id}: {str(e)}") from e

    @mcp.tool()
    async def get_automation_execution_details(
        workspace_id: int = Field(..., description="The ID of the workspace containing the automation."),
        automation_id: int = Field(..., description="The ID of the automation."),
        execution_id: int = Field(..., description="The ID of the specific execution run to retrieve details for.")
    ) -> AutomationLogItemDetailsDto:
        """
        Retrieves detailed information about a specific finished automation execution run.

        Args:
            workspace_id: The ID of the target workspace.
            automation_id: The ID of the target automation.
            execution_id: The ID of the specific execution run.

        Returns:
            An AutomationLogItemDetailsDto object with detailed execution information.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., execution not found).
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/automations/{automation_id}/executions/{execution_id}"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                details = AutomationLogItemDetailsDto.model_validate(response_data)
                return details
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for execution {execution_id} of automation {automation_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get details for execution {execution_id} of automation {automation_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting details for execution {execution_id}: {str(e)}") from e

    @mcp.tool()
    async def get_automation_state(
        workspace_id: int = Field(..., description="The ID of the workspace containing the automation."),
        automation_id: int = Field(..., description="The ID of the automation whose state is to be retrieved.")
    ) -> AutomationStateDto:
        """
        Retrieves the current state of a specific automation, including trigger, queue, and execution status.

        Args:
            workspace_id: The ID of the target workspace.
            automation_id: The ID of the target automation.

        Returns:
            An AutomationStateDto object describing the automation's current state.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/automations/{automation_id}/state"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                state = AutomationStateDto.model_validate(response_data)
                return state
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for state of automation {automation_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get state for automation {automation_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting state for automation {automation_id}: {str(e)}") from e

    @mcp.tool()
    async def get_active_automation_execution(
        workspace_id: int = Field(..., description="The ID of the workspace containing the automation."),
        automation_id: int = Field(..., description="The ID of the automation to check for active execution.")
    ) -> Optional[AutomationExecutionStateDto]:
        """
        Retrieves the state of the currently active execution for a specific automation, if one exists.

        Args:
            workspace_id: The ID of the target workspace.
            automation_id: The ID of the target automation.

        Returns:
            An AutomationExecutionStateDto object if an execution is active, otherwise None.

        Raises:
            SkyviaAPIError: If the API request fails for reasons other than 'not found'.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/automations/{automation_id}/active"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            # Check if the response is empty or indicates no active execution
            # The API might return 200 OK with an empty body/dict or specific fields being null,
            # or potentially a 404 if nothing is active. We need robustness here.
            if not response_data or not isinstance(response_data, dict):
                 # Assuming an empty/non-dict response means no active execution
                return None

            # Validate data using Pydantic - Check if essential fields are present to consider it "active"
            # A simple check could be if 'executionId' exists and is not null/zero
            if response_data.get("executionId"):
                state = AutomationExecutionStateDto.model_validate(response_data)
                return state
            else:
                 # Response received, but doesn't look like an active execution state object
                 return None

        except SkyviaAPIError as e:
            # Specifically handle 404 Not Found as "no active execution"
            if e.status_code == 404:
                return None
            # Re-raise other API errors
            raise SkyviaAPIError(f"Failed to get active execution for automation {automation_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting active execution for automation {automation_id}: {str(e)}") from e

    @mcp.tool()
    async def enable_automation(
        workspace_id: int = Field(..., description="The ID of the workspace containing the automation."),
        automation_id: int = Field(..., description="The ID of the automation to enable.")
    ) -> None:
        """
        Enables the trigger for the specified automation.

        Args:
            workspace_id: The ID of the target workspace.
            automation_id: The ID of the target automation to enable.

        Returns:
            None if successful.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/automations/{automation_id}/enable"
            # POST request, expecting 200 OK with no content
            await authenticated_request(endpoint=endpoint, method="POST")
            # No return needed on success (implicit None)
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to enable automation {automation_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while enabling automation {automation_id}: {str(e)}") from e

    @mcp.tool()
    async def disable_automation(
        workspace_id: int = Field(..., description="The ID of the workspace containing the automation."),
        automation_id: int = Field(..., description="The ID of the automation to disable.")
    ) -> None:
        """
        Disables the trigger for the specified automation.

        Args:
            workspace_id: The ID of the target workspace.
            automation_id: The ID of the target automation to disable.

        Returns:
            None if successful.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/automations/{automation_id}/disable"
            # POST request, expecting 200 OK with no content
            await authenticated_request(endpoint=endpoint, method="POST")
            # No return needed on success (implicit None)
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to disable automation {automation_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while disabling automation {automation_id}: {str(e)}") from e
