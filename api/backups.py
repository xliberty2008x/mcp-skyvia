"""
MCP Tools for Skyvia Backups API endpoints.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from .utils import authenticated_request, SkyviaAPIError

# --- Pydantic Models based on skyvia.json ---

class BackupDto(BaseModel):
    """Represents a Skyvia backup package."""
    id: int
    name: Optional[str] = None
    created: datetime
    modified: datetime
    scheduled: bool

class BackupDtoHasMorePagingDto(BaseModel):
    """Paging structure for BackupDto list."""
    data: Optional[List[BackupDto]] = None
    hasMore: bool

class BackupSnapshotLogDto(BaseModel):
    """Represents a log entry for a backup snapshot."""
    snapshotId: int
    queueTime: Optional[datetime] = None
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    state: str # Enum: "New", "Queued", "Running", "Succeeded", "Failed", "Canceling", "Canceled"
    runBySchedule: bool

class BackupSnapshotLogDtoHasMorePagingDto(BaseModel):
    """Paging structure for BackupSnapshotLogDto list."""
    data: Optional[List[BackupSnapshotLogDto]] = None
    hasMore: bool

class BackupSnapshotLogDetailsDto(BaseModel):
    """Detailed information about a backup snapshot execution."""
    snapshotId: int
    queueTime: Optional[datetime] = None
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    state: str # Enum from BackupSnapshotLogDto
    runBySchedule: bool
    result: Optional[str] = None # Error message on failure

class BackupActiveRunDto(BaseModel):
    """Represents the state of an active backup run."""
    runId: int # Note: Spec uses runId here, snapshot log uses snapshotId. Clarify if they are the same. Assuming runId refers to snapshotId for active runs.
    date: datetime # Likely start time
    duration: int # Assuming seconds
    state: str # Enum from BackupSnapshotLogDto

class BackupScheduleDto(BaseModel):
    """Represents the schedule status of a backup."""
    active: bool

# --- MCP Tools ---

def register_tools(mcp: FastMCP):
    """Registers backup-related tools with the MCP server."""

    @mcp.tool()
    async def list_backups(
        workspace_id: int = Field(..., description="The ID of the workspace containing the backups."),
        skip: int = Field(0, description="Number of backups to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of backups to return (for pagination). Must be between 1 and 200.", ge=1, le=200)
    ) -> BackupDtoHasMorePagingDto:
        """
        Retrieves a list of backup packages within a specific workspace.

        Args:
            workspace_id: The ID of the target workspace.
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).

        Returns:
            An object containing a list of backup DTOs and a 'hasMore' flag for pagination.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/backups"
            params = {"skip": skip, "take": take}
            response_data = await authenticated_request(endpoint=endpoint, method="GET", params=params)

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                backups_page = BackupDtoHasMorePagingDto.model_validate(response_data)
                return backups_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for backups in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to list backups for workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while listing backups for workspace {workspace_id}: {str(e)}") from e

    @mcp.tool()
    async def get_backup(
        workspace_id: int = Field(..., description="The ID of the workspace containing the backup."),
        backup_id: int = Field(..., description="The ID of the backup package to retrieve.")
    ) -> BackupDto:
        """
        Retrieves details for a specific backup package within a workspace.

        Args:
            workspace_id: The ID of the target workspace.
            backup_id: The ID of the target backup package.

        Returns:
            A BackupDto object with backup package details.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., backup not found).
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/backups/{backup_id}"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                backup_details = BackupDto.model_validate(response_data)
                return backup_details
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for backup {backup_id} in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get details for backup {backup_id} in workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting details for backup {backup_id} in workspace {workspace_id}: {str(e)}") from e

    @mcp.tool()
    async def get_backup_snapshots(
        workspace_id: int = Field(..., description="The ID of the workspace containing the backup."),
        backup_id: int = Field(..., description="The ID of the backup package whose snapshots are to be retrieved."),
        start_date: Optional[datetime] = Field(None, description="Filter snapshots started after this date/time."),
        end_date: Optional[datetime] = Field(None, description="Filter snapshots started before this date/time."),
        failed: Optional[bool] = Field(None, description="Filter only failed snapshots (true) or non-failed ones (false)."),
        skip: int = Field(0, description="Number of snapshots to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of snapshots to return (for pagination). Must be between 1 and 200.", ge=1, le=200),
        sort_order: str = Field("asc", description="Sort order: 'asc' (ascending) or 'desc' (descending).", pattern="^(asc|desc)$"),
        sort_by: str = Field("startTime", description="Field to sort by: 'startTime' or 'snapshotId'.", pattern="^(startTime|snapshotId)$")
    ) -> BackupSnapshotLogDtoHasMorePagingDto:
        """
        Retrieves the finished snapshot history for a specific backup package.

        Args:
            workspace_id: The ID of the target workspace.
            backup_id: The ID of the target backup package.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            failed: Optional filter for failed status.
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).
            sort_order: Sort order ('asc' or 'desc', default 'asc').
            sort_by: Field to sort by ('startTime' or 'snapshotId', default 'startTime').

        Returns:
            An object containing a list of backup snapshot log DTOs and a 'hasMore' flag.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/backups/{backup_id}/snapshots"
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

            # Remove None values from params
            params = {k: v for k, v in params.items() if v is not None}

            response_data = await authenticated_request(endpoint=endpoint, method="GET", params=params)

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                snapshots_page = BackupSnapshotLogDtoHasMorePagingDto.model_validate(response_data)
                return snapshots_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for snapshots of backup {backup_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get snapshots for backup {backup_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting snapshots for backup {backup_id}: {str(e)}") from e

    @mcp.tool()
    async def run_backup_snapshot(
        workspace_id: int = Field(..., description="The ID of the workspace containing the backup."),
        backup_id: int = Field(..., description="The ID of the backup package to run a snapshot for.")
    ) -> BackupActiveRunDto:
        """
        Starts a new snapshot run for the specified backup package.

        Args:
            workspace_id: The ID of the target workspace.
            backup_id: The ID of the target backup package.

        Returns:
            A BackupActiveRunDto object representing the initiated snapshot run.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., backup not found, another run active).
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/backups/{backup_id}/snapshots"
            # POST request to trigger the snapshot
            response_data = await authenticated_request(endpoint=endpoint, method="POST")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic - Spec indicates it returns BackupActiveRunDto
                active_run = BackupActiveRunDto.model_validate(response_data)
                return active_run
            elif response_data is None:
                 # If the API returns 200 OK with no body, it's unclear what state was initiated.
                 # Raise an error suggesting checking the status separately.
                 raise SkyviaAPIError(
                     message=f"Backup snapshot run for {backup_id} initiated but received no run details.",
                     details="Empty response received"
                 )
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received when running snapshot for backup {backup_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to run snapshot for backup {backup_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while running snapshot for backup {backup_id}: {str(e)}") from e

    @mcp.tool()
    async def get_backup_snapshot_details(
        workspace_id: int = Field(..., description="The ID of the workspace containing the backup."),
        backup_id: int = Field(..., description="The ID of the backup package."),
        snapshot_id: int = Field(..., description="The ID of the specific snapshot run to retrieve details for.")
    ) -> BackupSnapshotLogDetailsDto:
        """
        Retrieves detailed information about a specific finished backup snapshot run.

        Args:
            workspace_id: The ID of the target workspace.
            backup_id: The ID of the target backup package.
            snapshot_id: The ID of the specific snapshot run.

        Returns:
            A BackupSnapshotLogDetailsDto object with detailed snapshot information.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., snapshot not found).
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/backups/{backup_id}/snapshots/{snapshot_id}"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                details = BackupSnapshotLogDetailsDto.model_validate(response_data)
                return details
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for snapshot {snapshot_id} of backup {backup_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get details for snapshot {snapshot_id} of backup {backup_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting details for snapshot {snapshot_id}: {str(e)}") from e

    @mcp.tool()
    async def get_active_backup_run(
        workspace_id: int = Field(..., description="The ID of the workspace containing the backup."),
        backup_id: int = Field(..., description="The ID of the backup package to check for an active run.")
    ) -> Optional[BackupActiveRunDto]:
        """
        Retrieves the state of the currently active snapshot run for a specific backup, if one exists.

        Args:
            workspace_id: The ID of the target workspace.
            backup_id: The ID of the target backup package.

        Returns:
            A BackupActiveRunDto object if a snapshot run is active, otherwise None.

        Raises:
            SkyviaAPIError: If the API request fails for reasons other than 'not found'.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/backups/{backup_id}/snapshots/active"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            # Similar logic to get_active_automation_execution
            if not response_data or not isinstance(response_data, dict):
                return None # No active run

            # Check if essential fields indicate an active run
            if response_data.get("runId"): # Assuming runId presence indicates activity
                state = BackupActiveRunDto.model_validate(response_data)
                return state
            else:
                return None # Doesn't look like an active run object

        except SkyviaAPIError as e:
            # Handle 404 Not Found as "no active run"
            if e.status_code == 404:
                return None
            # Re-raise other API errors
            raise SkyviaAPIError(f"Failed to get active run for backup {backup_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting active run for backup {backup_id}: {str(e)}") from e

    @mcp.tool()
    async def get_backup_schedule(
        workspace_id: int = Field(..., description="The ID of the workspace containing the backup."),
        backup_id: int = Field(..., description="The ID of the backup package whose schedule status is to be retrieved.")
    ) -> BackupScheduleDto:
        """
        Retrieves the schedule status (active/inactive) for a specific backup package.

        Args:
            workspace_id: The ID of the target workspace.
            backup_id: The ID of the target backup package.

        Returns:
            A BackupScheduleDto object indicating if the schedule is active.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/backups/{backup_id}/schedule"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            if isinstance(response_data, dict):
                schedule_status = BackupScheduleDto.model_validate(response_data)
                return schedule_status
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for schedule of backup {backup_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get schedule for backup {backup_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting schedule for backup {backup_id}: {str(e)}") from e

    @mcp.tool()
    async def enable_backup_schedule(
        workspace_id: int = Field(..., description="The ID of the workspace containing the backup."),
        backup_id: int = Field(..., description="The ID of the backup package whose schedule should be enabled.")
    ) -> BackupScheduleDto:
        """
        Enables the schedule for the specified backup package.

        Args:
            workspace_id: The ID of the target workspace.
            backup_id: The ID of the target backup package.

        Returns:
            A BackupScheduleDto object reflecting the new state (should be active=True).

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/backups/{backup_id}/schedule/enable"
            # POST request, expects BackupScheduleDto in response
            response_data = await authenticated_request(endpoint=endpoint, method="POST")
            if isinstance(response_data, dict):
                schedule_status = BackupScheduleDto.model_validate(response_data)
                return schedule_status
            else:
                 raise SkyviaAPIError(
                    message=f"Unexpected response format received after enabling schedule for backup {backup_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to enable schedule for backup {backup_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while enabling schedule for backup {backup_id}: {str(e)}") from e

    @mcp.tool()
    async def disable_backup_schedule(
        workspace_id: int = Field(..., description="The ID of the workspace containing the backup."),
        backup_id: int = Field(..., description="The ID of the backup package whose schedule should be disabled.")
    ) -> BackupScheduleDto:
        """
        Disables the schedule for the specified backup package.

        Args:
            workspace_id: The ID of the target workspace.
            backup_id: The ID of the target backup package.

        Returns:
            A BackupScheduleDto object reflecting the new state (should be active=False).

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/backups/{backup_id}/schedule/disable"
            # POST request, expects BackupScheduleDto in response
            response_data = await authenticated_request(endpoint=endpoint, method="POST")
            if isinstance(response_data, dict):
                schedule_status = BackupScheduleDto.model_validate(response_data)
                return schedule_status
            else:
                 raise SkyviaAPIError(
                    message=f"Unexpected response format received after disabling schedule for backup {backup_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to disable schedule for backup {backup_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while disabling schedule for backup {backup_id}: {str(e)}") from e
