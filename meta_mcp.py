#!/usr/bin/env python
# meta_mcp_server.py
from mcp.server import Server
from mcp.types import Tool, TextContent
import subprocess
import json
from pathlib import Path

class MetaMCPServer:
    def __init__(self):
        self.server = Server("meta-mcp")
        self.active_servers = {}  # mcp_id -> process/client
        self.credentials = {}  # Load from secure store
        
    async def search_mcp(self, query: str) -> list[dict]:
        """Search embedding index for relevant MCP servers"""
        # Your current Chroma/Qdrant search
        results = await self.vector_search(query)
        
        return [{
            "id": result.id,
            "name": result.metadata["name"],
            "description": result.metadata["description"],
            "repo": result.metadata["repo"],
            "score": result.score
        } for result in results]
    
    async def get_functions(self, mcp_id: str) -> list[dict]:
        """Get tools from a specific MCP server"""
        # Start MCP server if not running
        if mcp_id not in self.active_servers:
            await self.start_mcp_server(mcp_id)
        
        client = self.active_servers[mcp_id]
        tools_response = await client.call_tool("tools/list", {})
        
        return tools_response["tools"]
    
    async def run_function(
        self, 
        mcp_id: str, 
        function_name: str, 
        arguments: dict,
        env_vars: dict = None
    ) -> dict:
        """Execute a function on a specific MCP server"""
        # Check if we have required credentials
        missing_creds = self.check_missing_credentials(mcp_id, env_vars)
        if missing_creds:
            return {
                "status": "needs_credentials",
                "required": missing_creds,
                "message": "Please provide required credentials"
            }
        
        # Ensure server is running with correct env
        await self.ensure_server_running(mcp_id, env_vars)
        
        client = self.active_servers[mcp_id]
        result = await client.call_tool(function_name, arguments)
        
        return result
    
    async def start_mcp_server(self, mcp_id: str, env_vars: dict = None):
        """Start an MCP server process"""
        metadata = self.get_server_metadata(mcp_id)
        
        # Build env with credentials
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # Start process
        process = subprocess.Popen(
            metadata["command"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=env,
            cwd=metadata["install_path"]
        )
        
        # Create MCP client connection
        client = await create_mcp_client(process.stdin, process.stdout)
        self.active_servers[mcp_id] = client
