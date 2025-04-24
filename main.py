"""
Skyvia MCP Server: Main entry point
"""
import sys
import argparse
from fastmcp import FastMCP
from api.config import (
    SERVER_NAME,
    SERVER_DESCRIPTION,
    SERVER_VERSION,
    SERVER_DEPENDENCIES,
    get_api_key,
    set_api_key
)

mcp = FastMCP(
    SERVER_NAME,
    description=SERVER_DESCRIPTION,
    dependencies=SERVER_DEPENDENCIES,
    version=SERVER_VERSION
)

# Register tool modules
from api import workspaces, connections, integrations, automations, backups, agents, account, endpoints
workspaces.register_tools(mcp)
connections.register_tools(mcp)
integrations.register_tools(mcp)
automations.register_tools(mcp)
backups.register_tools(mcp)
agents.register_tools(mcp)
account.register_tools(mcp)
endpoints.register_tools(mcp)
# automations.register_tools(mcp)
# backups.register_tools(mcp)
# connections.register_tools(mcp)
# endpoints.register_tools(mcp)
# integrations.register_tools(mcp)
# workspaces.register_tools(mcp)


def main():
    parser = argparse.ArgumentParser(description=SERVER_DESCRIPTION)
    parser.add_argument("--skyvia-api-token", help="Skyvia API Token", required=False)
    # Add other potential CLI args if needed

    # Parse only the --skyvia-api-token argument, leave the rest for FastMCP
    args, remaining_argv = parser.parse_known_args()

    # Initialize API Key - prioritize CLI arg, then ENV var (checked by get_api_key)
    try:
        if args.skyvia_api_token:
            set_api_key(args.skyvia_api_token)
            print("Using Skyvia API token from command line argument.")
        else:
            # Trigger check for environment variable
            get_api_key()
            print("Using Skyvia API token from environment variable.")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        # Exit if token is not configured
        sys.exit(1)

    # Pass the remaining arguments (unparsed by our parser) to FastMCP
    # The first element is the script name, which FastMCP expects
    sys.argv = [sys.argv[0]] + remaining_argv

    try:
        mcp.run()
    except Exception as e:
        print(f"MCP Server failed to run: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
