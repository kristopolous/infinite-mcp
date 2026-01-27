# InfiniteMCP

**A meta-MCP server that gives Claude access to the entire ecosystem of MCP servers through semantic search and dynamic tool discovery.**

[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## What is InfiniteMCP?

InfiniteMCP is a Model Context Protocol (MCP) server that acts as a universal gateway to thousands of other MCP servers. Instead of manually configuring each MCP server you want to use, InfiniteMCP lets Claude discover, understand, and use any MCP server on demand through natural language queries.

Think of it as an "MCP server of MCP servers" - a single connection that unlocks the entire MCP ecosystem.

## How It Works

```
Claude asks: "Search for MCP servers that can crawl websites"
    ↓
InfiniteMCP searches 1000+ indexed MCP servers
    ↓
Returns: [firecrawl-mcp, web-scraper-mcp, playwright-mcp, ...]
    ↓
Claude: "Use firecrawl to get content from example.com"
    ↓
InfiniteMCP dynamically loads firecrawl-mcp and executes the request
    ↓
Returns the crawled content to Claude
```

### The Three Core Functions

InfiniteMCP exposes three powerful tools to Claude:

1. **`search_mcp`** - Semantic search across all known MCP servers
   ```
   Input: "web search"
   Output: [brave-search-mcp, tavily-mcp, serper-mcp, ...]
   ```

2. **`get_functions`** - Discover what an MCP server can do
   ```
   Input: mcp_id (e.g., "brave-search-mcp")
   Output: [brave_web_search, brave_local_search, ...]
   ```

3. **`run_function`** - Execute a function from any MCP server
   ```
   Input: mcp_id, function_name, arguments, credentials
   Output: Function result
   ```

## Features

- 🔍 **Semantic Search** - Find MCP servers using natural language, powered by state-of-the-art embedding models
- 🚀 **Dynamic Loading** - MCP servers are loaded on-demand, no pre-configuration needed
- 🔐 **Smart Credential Management** - Securely handles API keys and credentials, with user prompts for missing values
- 🧩 **Tool Discovery** - Automatically discovers all available functions from any MCP server
- 📚 **Comprehensive Index** - Pre-indexed with 1000+ MCP servers from the ecosystem
- ⚡ **Efficient** - Caches connections and metadata for fast repeated access

## Installation

### Prerequisites

- Python 3.11+
- CUDA-capable GPU (recommended for embedding search)
- Node.js 18+ (for running discovered MCP servers)

### Setup
Local install requires a CUDA core

```bash
# Clone the repository
git clone https://github.com/yourusername/infinitemcp.git
cd infinitemcp

# Install dependencies
pip install -r requirements.txt

# Build the MCP server index (one-time setup)
./extracto
```

## Usage

### With Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "infinitemcp": {
      "command": "python",
      "args": ["-m", "infinitemcp"],
      "env": {
        "INFINITEMCP_DB": "/path/to/infinitemcp/db"
      }
    }
  }
}
```

### Example Interactions

**Discovering servers:**
```
You: "I need to search the web for information about MCP servers"
Claude: [uses search_mcp("web search")]
Claude: "I found several options. Brave Search looks good. Let me use that..."
```

**Using a server:**
```
Claude: [uses get_functions("brave-search-mcp")]
Claude: [uses run_function with brave_web_search]
Claude: "Here's what I found..."
```

**Handling credentials:**
```
Claude: [attempts run_function("github-mcp", ...)]
InfiniteMCP: "Missing required credential: GITHUB_TOKEN"
Claude: "I need your GitHub token to access that API..."
You: "Here it is: ghp_..."
Claude: [retries with credentials]
```

## Architecture

