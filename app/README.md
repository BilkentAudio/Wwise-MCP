# Wwise-MCP (Developer)

Python bridge for interacting with Wwise 2024.1 using the Model Context Protocol (MCP).

[![Python](https://img.shields.io/badge/Python-3.13%2B-blue)](https://www.python.org)

## Setup

1. Make sure Python 3.13+ is installed
2. Clone this repo and make sure you can access the python scripts in \scripts. 
3. Create a virtual environment in desired location:
   ```bash
   cd C:\path\to\your\project
   python3.13 -m venv .venv # On macOS
   py -3.13 -m venv .venv  # On Windows
   ```
4. Activate the virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # On macOS
   .venv\Scripts\activate     # On Windows
   ```
5. Install dependencies:
   ```bash
   pip install anyio fastmcp waapi-client 
   ```
6. Configure your MCP Client (i.e Claude Desktop) to use the Wwise-MCP server:
   ```bash
   {
     "mcpServers": 
     {
         "wwise-mcp": 
         {
           "command": "C:\\PathToYourPythonExe\\.venv\\Scripts\\python.exe",
           "args": ["C:\\PathToYour\\wwise_mcp.py"]
         }
     }
   }
   ```
7. Make sure to restart/save your MCP Client (i.e Claude Desktop) for Wwise-MCP to be registered.

You should make sure you have installed dependencies and/or are running in the `uv` virtual environment in order for the scripts to work.

## Troubleshooting

- Make sure Wwise Authoring is loaded and running before querying a wwise related request in the MCP client.
- Check logs in `wwise-mcp.log` for detailed error information
