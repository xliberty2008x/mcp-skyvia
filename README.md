# Skyvia API MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the [Skyvia Public API](https://skyvia.com/dev-center/rest-api-reference). It allows AI assistants and other MCP clients to securely access Skyvia functionalities like managing workspaces, connections, integrations, automations, and backups.

## Features

-   **Secure API Access:** Uses an API token provided via configuration (environment variable or command-line argument), avoiding exposure in client code or prompts.
-   **MCP Tool Interface:** Offers standardized MCP tools for common Skyvia operations.
-   **Modular Design:** Organizes API interactions based on Skyvia resource types.
-   **Smithery.ai Ready:** Designed for easy deployment on [smithery.ai](https://smithery.ai/) using a GitHub repository.

## Prerequisites

-   Python 3.9+
-   A Skyvia account and API Access Token. You can generate one in your Skyvia account under **Account > Access Tokens**.

## Setup & Running Locally

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd skyvia-mcp
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set the API Token:**
    You can provide the token in two ways:
    *   **Environment Variable (recommended):** Create a `.env` file in the project root:
        ```
        SKYVIA_API_TOKEN=your_skyvia_api_token_here
        ```
        The server will automatically load this using `python-dotenv`.
    *   **Command-line Argument:** Pass the token when running the server:
        ```bash
        python main.py --skyvia-api-token your_skyvia_api_token_here [fastmcp options...]
        ```

5.  **Run the server:**
    ```bash
    python main.py [fastmcp options...]
    ```
    Refer to the `fastmcp` documentation for options like setting the port (`--port 8000`).

## Available Tools

This server provides tools grouped by Skyvia resource type:

**Workspaces (`api/workspaces.py`)**
-   `list_workspaces`: Retrieves a list of all workspaces.
-   `get_workspace`: Retrieves details for a specific workspace.

**Connections (`api/connections.py`)**
-   `list_connections`: Retrieves a list of connections within a workspace.
-   `get_connection_details`: Retrieves detailed information for a specific connection.
-   `test_connection`: Tests a specified connection.

**Integrations (`api/integrations.py`)**
-   `list_integrations`: Retrieves a list of integration packages within a workspace.
-   `get_integration`: Retrieves details for a specific integration package.
-   `run_integration`: Starts an execution run for an integration package.
    *   *(Other integration tools like getting logs, canceling, scheduling are pending)*

**Automations (`api/automations.py`)**
-   `list_automations`: Retrieves a list of automations within a workspace.
-   `get_automation`: Retrieves details for a specific automation.
-   `get_automation_executions`: Retrieves the finished execution history for an automation.
-   `get_automation_execution_details`: Retrieves detailed information about a specific automation execution run.
-   `get_automation_state`: Retrieves the current state (trigger, queue, execution) of an automation.
-   `enable_automation`: Enables the trigger for an automation.
-   `disable_automation`: Disables the trigger for an automation.
-   `get_active_automation_execution`: Retrieves the state of the currently active execution, if any.

**Backups (`api/backups.py`)**
-   `list_backups`: Retrieves a list of backup packages within a workspace.
-   `get_backup`: Retrieves details for a specific backup package.
-   `get_backup_snapshots`: Retrieves the finished snapshot history for a backup.
-   `run_backup_snapshot`: Starts a new snapshot run for a backup package.
-   `get_backup_snapshot_details`: Retrieves detailed information about a specific snapshot run.
-   `get_active_backup_run`: Retrieves the state of the currently active snapshot run, if any.
-   `get_backup_schedule`: Retrieves the schedule status for a backup.
-   `enable_backup_schedule`: Enables the schedule for a backup.
-   `disable_backup_schedule`: Disables the schedule for a backup.

**Agents (`api/agents.py`)**
-   `list_agents`: Retrieves a list of agents within a workspace.
-   `get_agent`: Retrieves details for a specific agent.
-   `test_agent`: Tests a specified agent connection.

**Account (`api/account.py`)**
-   `get_account_users`: Retrieves a list of users belonging to the account.
-   `remove_account_user`: Removes a user from the account by email.
-   `get_account_invitations`: Retrieves a list of pending user invitations.
-   `invite_user`: Invites a new user to the account.
-   `resend_invitation`: Resends an invitation email.
-   `delete_invitation`: Deletes a pending invitation.

**Endpoints (`api/endpoints.py`)**
-   `list_endpoints`: Retrieves a list of endpoints within a workspace.
-   `get_endpoint_types`: Retrieves the mapping of endpoint type names to IDs (global).
-   `get_endpoint`: Retrieves details for a specific endpoint.
-   `enable_endpoint`: Enables a specified endpoint.
-   `disable_endpoint`: Disables a specified endpoint.
-   `get_endpoint_executions`: Retrieves the request log for an endpoint.
-   `get_endpoint_execution_details`: Retrieves detailed information about a specific endpoint request log entry.

## Deployment on Smithery.ai

1.  Ensure your Skyvia API token is configured as a secret or environment variable in your smithery.ai project settings (e.g., named `SKYVIA_API_TOKEN`).
2.  Configure the smithery.ai MCP server connection to run the command, passing the token:
    ```
    python main.py --skyvia-api-token ${SKYVIA_API_TOKEN}
    ```
    (Adjust the variable name `${SKYVIA_API_TOKEN}` if you named it differently in Smithery).

## Contributing

*(Details TBD)*
