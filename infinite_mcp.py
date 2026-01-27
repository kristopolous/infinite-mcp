#!/usr/bin/env python3
"""
InfiniteMCP Server - A meta-MCP server for discovering and using other MCP servers

Provides three main tools:
1. search_mcp - Search for relevant MCP servers, returns structured config
2. list_tools - Get available functions from a specific MCP server
3. execute_function - Run a function from an MCP server with parameters and credentials
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import mcp.types as types
import httpx
import subprocess
import json
import os
from typing import Any
import asyncio

# Configuration
SEARCH_API_URL = "https://day50.dev/infinite/search"

app = Server("infinitemcp")


@app.list_tools()
async def handle_list_tools() -> list[Tool]:  # <-- Changed name
    """List available tools for InfiniteMCP"""
    return [
        Tool(
            name="search_mcp",
            description="Search for MCP servers by functionality. Returns structured configs with commands and required credentials.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query describing what you want to do (e.g., 'web search', 'github integration', 'file system access')"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_tools",
            description="Get all available functions/tools from a specific MCP server. Use the config from search_mcp results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "config": {
                        "type": "object",
                        "description": "The MCP server config object from search_mcp results",
                        "properties": {
                            "one_liner": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Command to run the server"
                            },
                            "requires": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Required environment variables"
                            }
                        }
                    }
                },
                "required": ["config"]
            }
        ),
        Tool(
            name="execute_function",
            description="Execute a specific function from an MCP server. Handles credentials and parameters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "config": {
                        "type": "object",
                        "description": "The MCP server config object from search_mcp results",
                        "properties": {
                            "one_liner": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "requires": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "function_name": {
                        "type": "string",
                        "description": "The name of the function to execute (from list_tools results)"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Function parameters as a JSON object",
                        "default": {}
                    },
                    "env_vars": {
                        "type": "object",
                        "description": "Environment variables needed (API keys, tokens, etc.). Keys should match the 'requires' field.",
                        "default": {}
                    }
                },
                "required": ["config", "function_name"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls"""
    
    if name == "search_mcp":
        return await search_mcp(arguments)
    elif name == "list_tools":
        return await list_mcp_tools(arguments)
    elif name == "execute_function":
        return await execute_function(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def search_mcp(arguments: dict) -> list[TextContent]:
    """Search for MCP servers using the search API"""
    query = arguments["query"]
    limit = arguments.get("limit", 5)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                SEARCH_API_URL,
                params={"q": query},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
        
        
        results = data.get("results", [])
        
        if not results:
            return [TextContent(
                type="text",
                text=f"No MCP servers found matching '{query}'. Try a different search term."
            )]
        
        # Return structured JSON that Claude can use
        output = f"# Found {len(results)} MCP servers for: '{query}'\n\n"
        output += "```json\n"
        output += json.dumps(results, indent=2)
        output += "\n```\n\n"
        output += "To use a server:\n"
        output += "1. Call `list_tools` with the config object to see available functions\n"
        output += "2. Call `execute_function` with the config, function name, and any required env_vars\n"
        
        return [TextContent(type="text", text=output)]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error searching MCP servers: {str(e)}"
        )]


async def list_mcp_tools(arguments: dict) -> list[TextContent]:
    """List tools available in a specific MCP server"""
    config = arguments["config"]
    one_liner = config.get("one_liner", [])
    requires = config.get("requires", [])
    
    if not one_liner:
        return [TextContent(
            type="text",
            text="Error: Invalid config - missing 'one_liner' command"
        )]
    
    try:
        # Start the MCP server and query its tools
        tools = await query_mcp_server_tools(one_liner)
        
        if not tools:
            return [TextContent(
                type="text",
                text=f"No tools found for MCP server: {' '.join(one_liner)}"
            )]
        
        output = f"# Tools available in: {' '.join(one_liner)}\n\n"
        
        if requires:
            output += f"**Required environment variables**: {', '.join(requires)}\n\n"
        
        output += "## Available Functions\n\n"
        
        for tool in tools:
            output += f"### {tool['name']}\n"
            output += f"{tool.get('description', 'No description')}\n\n"
            output += f"**Parameters**:\n```json\n{json.dumps(tool.get('inputSchema', {}), indent=2)}\n```\n\n"
        
        output += f"\n**To execute**: Use `execute_function` with this config and the function name.\n"
        
        return [TextContent(type="text", text=output)]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error listing tools: {str(e)}\n\n"
                 f"The server may need to be installed or may require credentials.\n"
                 f"Command attempted: {' '.join(one_liner)}"
        )]


async def execute_function(arguments: dict) -> list[TextContent]:
    """Execute a function from an MCP server"""
    config = arguments["config"]
    function_name = arguments["function_name"]
    parameters = arguments.get("parameters", {})
    env_vars = arguments.get("env_vars", {})
    
    one_liner = config.get("one_liner", [])
    requires = config.get("requires", [])
    
    if not one_liner:
        return [TextContent(
            type="text",
            text="Error: Invalid config - missing 'one_liner' command"
        )]
    
    # Check for missing credentials
    missing = [req for req in requires if req not in env_vars]
    if missing:
        return [TextContent(
            type="text",
            text=f"⚠️  Missing required credentials\n\n"
                 f"Required: {', '.join(requires)}\n"
                 f"Missing: {', '.join(missing)}\n\n"
                 f"Please call execute_function again with env_vars containing these credentials."
        )]
    
    try:
        # Execute the function
        result = await execute_mcp_function(
            command=one_liner,
            function_name=function_name,
            parameters=parameters,
            env_vars=env_vars
        )
        
        # Format result
        output = f"# Result from {function_name}\n\n"
        output += "```json\n"
        output += json.dumps(result, indent=2)
        output += "\n```"
        
        return [TextContent(type="text", text=output)]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing {function_name}: {str(e)}\n\n"
                 f"Command: {' '.join(one_liner)}\n"
                 f"Parameters: {json.dumps(parameters, indent=2)}"
        )]


# Helper functions (stubs to be implemented)

async def query_mcp_server_tools(command: list[str]) -> list[dict]:
    """
    Start an MCP server and query its available tools
    
    TODO: Implement actual MCP client connection via stdio
    """
    # This will:
    # 1. Start subprocess pith command
    # 2. Connect via MCP stdio protocol
    # 3. Send initialize request
    # 4. Send tools/list request
    # 5. Return tools
    
    return [
        {
            "name": "example_tool",
            "description": "This is a placeholder - actual implementation needed",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "param": {"type": "string"}
                }
            }
        }
    ]


async def execute_mcp_function(
    command: list[str],
    function_name: str,
    parameters: dict,
    env_vars: dict
) -> dict:
    """
    Execute a function on an MCP server
    
    TODO: Implement actual MCP client connection and tool execution
    """
    
    return {
        "status": "success",
        "result": "This is a placeholder - actual implementation needed",
        "function": function_name,
        "parameters": parameters
    }


async def main():
    """Run the InfiniteMCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import sys
    import signal
    
    def signal_handler(sig, frame):
        print("\nShutting down...", file=sys.stderr)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    asyncio.run(main(), debug=True)
