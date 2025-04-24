"""
MCP Tools for Skyvia Agents API endpoints.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from .utils import authenticated_request, SkyviaAPIError
from .connections import ApiResult # Re-use ApiResult from connections module

# --- Pydantic Models based on skyvia.json ---

class AgentDto(BaseModel):
    """Represents a Skyvia Agent."""
    id: int
    name: Optional[str] = None
    key: Optional[str] = None # Agent key might be sensitive, consider redacting/omitting in logs if needed

class AgentDtoHasMorePagingDto(BaseModel):
    """Paging structure for AgentDto list."""
    data: Optional[List[AgentDto]] = None
    hasMore: bool

# --- MCP Tools ---

def register_tools(mcp: FastMCP):
    """Registers agent-related tools with the MCP server."""

    @mcp.tool()
    async def list_agents(
        workspace_id: int = Field(..., description="The ID of the workspace containing the agents."),
        skip: int = Field(0, description="Number of agents to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of agents to return (for pagination). Must be between 1 and 200.", ge=1, le=200)
    ) -> AgentDtoHasMorePagingDto:
        """
        Retrieves a list of agents within a specific workspace.

        Args:
            workspace_id: The ID of the target workspace.
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).

        Returns:
            An object containing a list of agent DTOs and a 'hasMore' flag for pagination.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/agents"
            params = {"skip": skip, "take": take}
            response_data = await authenticated_request(endpoint=endpoint, method="GET", params=params)

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                agents_page = AgentDtoHasMorePagingDto.model_validate(response_data)
                return agents_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for agents in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to list agents for workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while listing agents for workspace {workspace_id}: {str(e)}") from e

    @mcp.tool()
    async def get_agent(
        workspace_id: int = Field(..., description="The ID of the workspace containing the agent."),
        agent_id: int = Field(..., description="The ID of the agent to retrieve.")
    ) -> AgentDto:
        """
        Retrieves details for a specific agent within a workspace.

        Args:
            workspace_id: The ID of the target workspace.
            agent_id: The ID of the target agent.

        Returns:
            An AgentDto object with agent details.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., agent not found).
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/agents/{agent_id}"
            response_data = await authenticated_request(endpoint=endpoint, method="GET")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                agent_details = AgentDto.model_validate(response_data)
                return agent_details
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for agent {agent_id} in workspace {workspace_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to get details for agent {agent_id} in workspace {workspace_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while getting details for agent {agent_id} in workspace {workspace_id}: {str(e)}") from e

    @mcp.tool()
    async def test_agent(
        workspace_id: int = Field(..., description="The ID of the workspace containing the agent."),
        agent_id: int = Field(..., description="The ID of the agent to test.")
    ) -> ApiResult:
        """
        Tests the specified agent connection within a workspace.

        Args:
            workspace_id: The ID of the target workspace.
            agent_id: The ID of the target agent to test.

        Returns:
            An ApiResult object, typically containing a success or failure message.

        Raises:
            SkyviaAPIError: If the API request fails or the test itself indicates an error.
        """
        try:
            endpoint = f"/v1/workspaces/{workspace_id}/agents/{agent_id}/test"
            # POST request to trigger the test
            response_data = await authenticated_request(endpoint=endpoint, method="POST")

            if isinstance(response_data, dict):
                 # Validate data using Pydantic
                result = ApiResult.model_validate(response_data)
                # Check message for failure indicators
                if "error" in (result.message or "").lower() or "fail" in (result.message or "").lower():
                     raise SkyviaAPIError(message=f"Agent test failed: {result.message}", details=result)
                return result
            elif response_data is None:
                 # Assume success if no content is returned on 200 OK
                 return ApiResult(message="Agent test initiated successfully (No content returned).", refresh=False)
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for testing agent {agent_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            # Add context to failure
            if e.status_code and e.status_code >= 400:
                 raise SkyviaAPIError(f"Failed to initiate test for agent {agent_id}: {e}", status_code=e.status_code, details=e.details) from e
            else: # Already a failure message from logic above
                 raise e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while testing agent {agent_id}: {str(e)}") from e
