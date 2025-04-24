"""
MCP Tools for Skyvia Account API endpoints.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from fastmcp import FastMCP
from .utils import authenticated_request, SkyviaAPIError

# --- Pydantic Models based on skyvia.json ---

class AccountWorkspaceUserDto(BaseModel):
    """Represents a user's role within a specific workspace (in account context)."""
    workspaceId: int
    roleName: Optional[str] = None
    roleId: int

class AccountUserDto(BaseModel):
    """Represents a user within the Skyvia account."""
    id: Optional[int] = None # User ID might not always be present? Spec says nullable
    email: Optional[EmailStr] = None
    fullName: Optional[str] = None
    type: str # Enum: "Administrator", "Member"
    workspaces: Optional[List[AccountWorkspaceUserDto]] = None

class AccountUserDtoHasMorePagingDto(BaseModel):
    """Paging structure for AccountUserDto list."""
    data: Optional[List[AccountUserDto]] = None
    hasMore: bool

class AccountInvitedUserDto(BaseModel):
    """Represents an invited user within the Skyvia account."""
    id: int # Invitation ID
    email: Optional[EmailStr] = None
    type: str # Enum: "Administrator", "Member"
    workspaces: Optional[List[AccountWorkspaceUserDto]] = None
    invitationDate: datetime
    userId: Optional[int] = None # User ID if they accepted
    fullName: Optional[str] = None # Populated if user accepted

class AccountInvitedUserDtoHasMorePagingDto(BaseModel):
    """Paging structure for AccountInvitedUserDto list."""
    data: Optional[List[AccountInvitedUserDto]] = None
    hasMore: bool

class InviteToWorkspaceDto(BaseModel):
    """Specifies workspace and role for an invitation."""
    workspaceId: int
    roleId: int

class InviteUserRequestDto(BaseModel):
    """Request body for inviting a user."""
    email: EmailStr
    userType: str # Enum: "Administrator", "Member"
    workspaces: Optional[List[InviteToWorkspaceDto]] = None

class InvitedUserStatusDto(BaseModel):
    """Response after inviting or resending an invitation."""
    email: Optional[EmailStr] = None
    status: Optional[str] = None # e.g., "Invited", "AlreadyMember"
    invitationId: int

class RemoveAccountUserRequestDto(BaseModel):
    """Request body for removing a user."""
    email: Optional[EmailStr] = None # Assuming email identifies the user to remove

# --- MCP Tools ---

def register_tools(mcp: FastMCP):
    """Registers account-related tools with the MCP server."""

    @mcp.tool()
    async def get_account_users(
        searchMask: Optional[str] = Field(None, description="Optional search filter by user name part."),
        skip: int = Field(0, description="Number of users to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of users to return (for pagination). Must be between 1 and 200.", ge=1, le=200)
    ) -> AccountUserDtoHasMorePagingDto:
        """
        Retrieves a list of users belonging to the account.

        Args:
            searchMask: Optional filter for user name.
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).

        Returns:
            An object containing a list of account user DTOs and a 'hasMore' flag.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = "/v1/account/users"
            params = {"skip": skip, "take": take}
            if searchMask:
                params["searchMask"] = searchMask

            response_data = await authenticated_request(endpoint=endpoint, method="GET", params=params)

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                users_page = AccountUserDtoHasMorePagingDto.model_validate(response_data)
                return users_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for account users: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to list account users: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while listing account users: {str(e)}") from e

    @mcp.tool()
    async def remove_account_user(
        email: EmailStr = Field(..., description="The email address of the user to remove from the account.")
    ) -> None:
        """
        Removes a user from the Skyvia account using their email address.

        Args:
            email: The email address of the user to remove.

        Returns:
            None if successful.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., user not found, permissions error).
        """
        try:
            endpoint = "/v1/account/users"
            request_body = RemoveAccountUserRequestDto(email=email)
            # DELETE request with a body
            await authenticated_request(
                endpoint=endpoint,
                method="DELETE",
                json_data=request_body.model_dump(exclude_none=True) # Send email in body
            )
            # No return needed on success (implicit None)
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to remove account user {email}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while removing account user {email}: {str(e)}") from e

    @mcp.tool()
    async def get_account_invitations(
        skip: int = Field(0, description="Number of invitations to skip (for pagination). Must be >= 0.", ge=0),
        take: int = Field(20, description="Number of invitations to return (for pagination). Must be between 1 and 200.", ge=1, le=200)
    ) -> AccountInvitedUserDtoHasMorePagingDto:
        """
        Retrieves a list of pending user invitations for the account.

        Args:
            skip: Items to skip (default 0).
            take: Items to take (default 20, max 200).

        Returns:
            An object containing a list of invited user DTOs and a 'hasMore' flag.

        Raises:
            SkyviaAPIError: If the API request fails.
        """
        try:
            endpoint = "/v1/account/invitations"
            params = {"skip": skip, "take": take}
            response_data = await authenticated_request(endpoint=endpoint, method="GET", params=params)

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                invitations_page = AccountInvitedUserDtoHasMorePagingDto.model_validate(response_data)
                return invitations_page
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received for account invitations: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to list account invitations: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while listing account invitations: {str(e)}") from e

    @mcp.tool()
    async def invite_user(
        email: EmailStr = Field(..., description="Email address of the user to invite."),
        user_type: str = Field(..., description="Type of the user: 'Administrator' or 'Member'.", pattern="^(Administrator|Member)$"),
        workspaces: Optional[List[InviteToWorkspaceDto]] = Field(None, description="Optional list of workspaces and roles to assign the user to.")
    ) -> InvitedUserStatusDto:
        """
        Invites a new user to the Skyvia account.

        Args:
            email: The email address of the user to invite.
            user_type: The type of account role ('Administrator' or 'Member').
            workspaces: Optional list specifying workspace IDs and role IDs.

        Returns:
            An InvitedUserStatusDto object indicating the status and invitation ID.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., invalid email, user already exists).
        """
        try:
            endpoint = "/v1/account/invitations"
            request_body = InviteUserRequestDto(
                email=email,
                userType=user_type, # Match casing from spec
                workspaces=workspaces
            )
            response_data = await authenticated_request(
                endpoint=endpoint,
                method="POST",
                json_data=request_body.model_dump(exclude_none=True)
            )

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                status = InvitedUserStatusDto.model_validate(response_data)
                return status
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received when inviting user {email}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to invite user {email}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while inviting user {email}: {str(e)}") from e

    @mcp.tool()
    async def resend_invitation(
        invitation_id: int = Field(..., description="The ID of the invitation to resend.")
    ) -> InvitedUserStatusDto:
        """
        Resends an invitation email for a pending invitation.

        Args:
            invitation_id: The ID of the invitation to resend.

        Returns:
            An InvitedUserStatusDto object indicating the status after resending.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., invitation not found or already accepted).
        """
        try:
            endpoint = f"/v1/account/invitations/{invitation_id}/resend"
            # POST request to trigger the resend
            response_data = await authenticated_request(endpoint=endpoint, method="POST")

            if isinstance(response_data, dict):
                # Validate data using Pydantic
                status = InvitedUserStatusDto.model_validate(response_data)
                return status
            else:
                raise SkyviaAPIError(
                    message=f"Unexpected response format received when resending invitation {invitation_id}: {type(response_data)}",
                    details=response_data
                )
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to resend invitation {invitation_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while resending invitation {invitation_id}: {str(e)}") from e

    @mcp.tool()
    async def delete_invitation(
        invitation_id: int = Field(..., description="The ID of the invitation to delete.")
    ) -> None:
        """
        Deletes a pending invitation from the account.

        Args:
            invitation_id: The ID of the invitation to delete.

        Returns:
            None if successful.

        Raises:
            SkyviaAPIError: If the API request fails (e.g., invitation not found).
        """
        try:
            endpoint = f"/v1/account/invitations/{invitation_id}"
            # DELETE request, expecting 200 OK with no content
            await authenticated_request(endpoint=endpoint, method="DELETE")
            # No return needed on success
        except SkyviaAPIError as e:
            raise SkyviaAPIError(f"Failed to delete invitation {invitation_id}: {e}", status_code=e.status_code, details=e.details) from e
        except Exception as e:
            raise SkyviaAPIError(f"An unexpected error occurred while deleting invitation {invitation_id}: {str(e)}") from e
