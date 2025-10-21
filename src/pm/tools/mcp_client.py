"""
On-demand MCP Client using official MCP library.

Uses the official MCP client/server pattern for resource efficiency and proper protocol handling.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters


class OnDemandMCPClient:
    """
    MCP Client using official MCP library for on-demand server execution.

    Benefits:
    - Resource efficiency: Server only runs when needed
    - Process isolation: Server failures don't crash orchestrator
    - Official MCP protocol: Uses standard MCP client/server pattern
    - Automatic initialization: Handles MCP handshake automatically
    """

    def __init__(self, server_script_path: Optional[str] = None):
        """Initialize the MCP client with server script path."""
        self.server_script_path = server_script_path or self._get_default_server_path()
        self.server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_script_path]
        )

    def _get_default_server_path(self) -> str:
        """Get the default path to the MCP server script."""
        # Assume we're in src/pm/tools/ and server is in same directory
        current_dir = Path(__file__).parent
        server_path = current_dir / "mcp_server.py"
        return str(server_path.absolute())

    async def _execute_with_mcp_session(self, operation_func) -> Any:
        """Execute an operation with a managed MCP session."""
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize session
                    await session.initialize()

                    # Execute the operation
                    return await operation_func(session)

        except Exception as e:
            raise RuntimeError(f"MCP session error: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Call an MCP tool using the official MCP client library.

        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments

        Returns:
            List of result dictionaries (parsed from content responses)
        """
        start_time = datetime.now()

        async def _tool_operation(session: ClientSession):
            # Call the tool
            call_result = await session.call_tool(tool_name, arguments)

            # Process the response content
            results = []
            for content in call_result.content:
                if hasattr(content, 'text'):
                    try:
                        # Try to parse as JSON
                        result_data = json.loads(content.text)
                        results.append(result_data)
                    except json.JSONDecodeError:
                        # If not JSON, wrap as text result
                        results.append({
                            "success": True,
                            "text_content": content.text
                        })

            return results

        try:
            results = await self._execute_with_mcp_session(_tool_operation)
            execution_time = (datetime.now() - start_time).total_seconds()

            # Add execution metadata
            for result in results:
                if isinstance(result, dict):
                    result["_mcp_execution_time"] = execution_time
                    result["_mcp_tool"] = tool_name

            return results

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_result = {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "arguments": arguments,
                "_mcp_execution_time": execution_time,
                "_mcp_error": True
            }
            return [error_result]

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools using the official MCP client library."""

        async def _list_operation(session: ClientSession):
            # List tools
            tools_result = await session.list_tools()

            # Convert tools to dictionaries
            tools_list = []
            for tool in tools_result.tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description or ""
                }
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    tool_dict["inputSchema"] = tool.inputSchema
                tools_list.append(tool_dict)

            return tools_list

        try:
            return await self._execute_with_mcp_session(_list_operation)

        except Exception as e:
            return [{
                "name": "error",
                "description": f"Failed to list tools: {e}",
                "error": True
            }]

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "client_type": "official_mcp_library",
            "server_script_path": self.server_script_path,
            "server_command": self.server_params.command,
            "server_args": self.server_params.args,
            "benefits": [
                "Resource efficiency - server only runs when needed",
                "Process isolation - failures don't crash orchestrator",
                "Official MCP protocol - uses standard MCP client/server pattern",
                "Automatic initialization - handles MCP handshake automatically",
                "Proper error handling - standard MCP error responses",
                "Session management - automatic cleanup and lifecycle"
            ]
        }