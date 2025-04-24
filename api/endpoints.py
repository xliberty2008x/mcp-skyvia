"""
MCP Tools for Skyvia Endpoints API endpoints.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from .utils import authenticated_request, SkyviaAPIError

# --- Pydantic Models based on skyvia.json ---

class EndpointDto(BaseModel):
    """Represents a Skyvia data endpoint."""
    id: int
    name: Optional[str] = None
    token: Optional[str] = None # Endpoint access token (potentially sensitive)
    active: bool
    type: str # Enum: "OData", "Sql"
    created: datetime
    modified: datetime

class EndpointDtoHasMorePagingDto(BaseModel):
    """Paging structure for EndpointDto list."""
    data: Optional[List[EndpointDto]] = None
    hasMore: bool

class EndpointRequestLogDto(BaseModel):
    """Represents a log entry for an endpoint request."""
    executionId: Optional[str] = None # Spec shows string, nullable
    date: datetime
    method: str # Enum: "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE"
    failed: bool
    bytes: int
    remoteIP: Optional[str] = None
    url: Optional[str] = None

class EndpointRequestLogDtoHasMorePagingDto(BaseModel):
    """Paging structure for EndpointRequestLogDto list."""
    data: Optional[List[EndpointRequestLogDto]] = None
    hasMore: bool

class EndpointRequestLogDetailedDto(BaseModel):
    """Detailed log information for an endpoint request."""
    date: datetime
    url: Optional[str] = None
    method: Optional[str] = None
    remoteIP: Optional[str] = None
    userAgent: Optional[str] = None
    user: Optional[str] = None
    error: Optional[str] = None
    log: Optional[List[str]] = None
    bytes: int
    rows: int
    pageToken: Optional[str] = None
    external: bool

class EndpointTypesDto(BaseModel):
    """Represents the mapping of endpoint type names to IDs."""
    OData: Optional[int] = None
    Sql: Optional[int] = None
    # Allow others for future compatibility
    model_config = {"extra": "allow"}


# --- MCP Tools ---

def register_tools(mcp: FastMCP):
    """Registers endpoint-related tools with the MCP server."""

    @mcp.tool()
    async def list_endpoints(
        workspace_id: int = Field(..., description="The ID of the workspace containing the endpoints."),
        skip: int = Field(0, description="Number of endpoints to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of endpoints to return (for pagination). Must be between 1 and 200.", ge=1, le=200)
    ) -> EndpointDtoHasMorePagingDto:
        """
        Retrieves a list of endpoints within a specific workspace.

        Args:
            workspace_id: The ID of the target workspace.
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).

        Returns:
            An object containing a list of endpoint DTOs and a 'hasMore' flag.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint_path = f"/v1/workspaces/{workspace_id}/endpoints"
            params = {"skip": skip, "take": take}
            response_data = await authenticated_request(endpoint=endpoint_path, method="GET", params=params)

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                endpoints_page = EndpointDtoHasMorePagingDto.model_validate(response_data)
                return endpoints_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for endpoints in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to list endpoints for workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while listing endpoints for workspace {workspace_id}: {str(e)}") from e

    @mcp.tool()
    async def get_endpoint_types() -> EndpointTypesDto:
        """
        Retrieves the mapping of endpoint type names (e.g., 'OData', 'Sql') to their internal IDs.
        This is a global endpoint, not specific to a workspace.

        Returns:
            An EndpointTypesDto object mapping type names to IDs.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint_path = "/v1/endpoints/types"
            response_data = await authenticated_request(endpoint=endpoint_path, method="GET")

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                types_map = EndpointTypesDto.model_validate(response_data)
                return types_map
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for endpoint types: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get endpoint types: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting endpoint types: {str(e)}") from e

    @mcp.tool()
    async def get_endpoint(
        workspace_id: int = Field(..., description="The ID of the workspace containing the endpoint."),
        endpoint_id: int = Field(..., description="The ID of the endpoint to retrieve.")
    ) -> EndpointDto:
        """
        Retrieves details for a specific endpoint within a workspace.

        Args:
            workspace_id: The ID of the target workspace.
            endpoint_id: The ID of the target endpoint.

        Returns:
            An EndpointDto object with endpoint details.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., endpoint not found).
        """
        try:
            endpoint_path = f"/v1/workspaces/{workspace_id}/endpoints/{endpoint_id}"
            response_data = await authenticated_request(endpoint=endpoint_path, method="GET")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                endpoint_details = EndpointDto.model_validate(response_data)
                return endpoint_details
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for endpoint {endpoint_id} in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get details for endpoint {endpoint_id} in workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting details for endpoint {endpoint_id}: {str(e)}") from e

    @mcp.tool()
    async def enable_endpoint(
        workspace_id: int = Field(..., description="The ID of the workspace containing the endpoint."),
        endpoint_id: int = Field(..., description="The ID of the endpoint to enable.")
    ) -> None:
        """
        Enables the specified endpoint.

        Args:
            workspace_id: The ID of the target workspace.
            endpoint_id: The ID of the target endpoint to enable.

        Returns:
            None if successful.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint_path = f"/v1/workspaces/{workspace_id}/endpoints/{endpoint_id}/enable"
            # POST request, expecting 200 OK with no content
            await authenticated_request(endpoint=endpoint_path, method="POST")
            # No return needed on success
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to enable endpoint {endpoint_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while enabling endpoint {endpoint_id}: {str(e)}") from e

    @mcp.tool()
    async def disable_endpoint(
        workspace_id: int = Field(..., description="The ID of the workspace containing the endpoint."),
        endpoint_id: int = Field(..., description="The ID of the endpoint to disable.")
    ) -> None:
        """
        Disables the specified endpoint.

        Args:
            workspace_id: The ID of the target workspace.
            endpoint_id: The ID of the target endpoint to disable.

        Returns:
            None if successful.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint_path = f"/v1/workspaces/{workspace_id}/endpoints/{endpoint_id}/disable"
            # POST request, expecting 200 OK with no content
            await authenticated_request(endpoint=endpoint_path, method="POST")
            # No return needed on success
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to disable endpoint {endpoint_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while disabling endpoint {endpoint_id}: {str(e)}") from e

    @mcp.tool()
    async def get_endpoint_executions(
        workspace_id: int = Field(..., description="The ID of the workspace containing the endpoint."),
        endpoint_id: int = Field(..., description="The ID of the endpoint whose request log is to be retrieved."),
        start_date: Optional[datetime] = Field(None, description="Filter requests after this date/time."),
        end_date: Optional[datetime] = Field(None, description="Filter requests before this date/time."),
        failed: Optional[bool] = Field(None, description="Filter only failed requests (true) or non-failed ones (false)."),
        skip: int = Field(0, description="Number of log entries to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of log entries to return (for pagination). Must be between 1 and 200.", ge=1, le=200),
        sort_order: str = Field("asc", description="Sort order: 'asc' (ascending) or 'desc' (descending).", pattern="^(asc|desc)$"),
        sort_by: str = Field("date", description="Field to sort by: 'date' or 'executionId'.", pattern="^(date|executionId)$") # Assuming executionId is valid here too, based on other log endpoints
    ) -> EndpointRequestLogDtoHasMorePagingDto:
        """
        Retrieves the request log (executions) for a specific endpoint.

        Args:
            workspace_id: The ID of the target workspace.
            endpoint_id: The ID of the target endpoint.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            failed: Optional filter for failed status.
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).
            sort_order: Sort order ('asc' or 'desc', default 'asc').
            sort_by: Field to sort by ('date' or 'executionId', default 'date').

        Returns:
            An object containing a list of endpoint request log DTOs and a 'hasMore' flag.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint_path = f"/v1/workspaces/{workspace_id}/endpoints/{endpoint_id}/executions"
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

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            response_data = await authenticated_request(endpoint=endpoint_path, method="GET", params=params)

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                executions_page = EndpointRequestLogDtoHasMorePagingDto.model_validate(response_data)
                return executions_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for executions of endpoint {endpoint_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get executions for endpoint {endpoint_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting executions for endpoint {endpoint_id}: {str(e)}") from e

    @mcp.tool()
    async def get_endpoint_execution_details(
        workspace_id: int = Field(..., description="The ID of the workspace containing the endpoint."),
        endpoint_id: int = Field(..., description="The ID of the endpoint."),
        record_id: str = Field(..., description="The ID of the specific execution record (log entry) to retrieve details for.")
    ) -> EndpointRequestLogDetailedDto:
        """
        Retrieves detailed information about a specific endpoint request log entry.

        Args:
            workspace_id: The ID of the target workspace.
            endpoint_id: The ID of the target endpoint.
            record_id: The ID of the specific execution record (obtained from get_endpoint_executions).

        Returns:
            An EndpointRequestLogDetailedDto object with detailed execution information.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., record not found).
        """
        try:
            # Note: record_id is a string in the path parameter according to the spec
            endpoint_path = f"/v1/workspaces/{workspace_id}/endpoints/{endpoint_id}/executions/{record_id}"
            response_data = await authenticated_request(endpoint=endpoint_path, method="GET")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                details = EndpointRequestLogDetailedDto.model_validate(response_data)
                return details
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for execution details {record_id} of endpoint {endpoint_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get details for execution {record_id} of endpoint {endpoint_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting details for execution {record_id}: {str(e)}") from e
