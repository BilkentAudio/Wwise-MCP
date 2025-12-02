# Installation

## Prerequisites
- Install [Claude Desktop](https://www.claude.com/download) or any MCP compatible AI agent
- Install [Wwise v2024.1+](https://www.audiokinetic.com/en/download/)
- Install [Wwise-MCP](https://github.com/t90786613/TestRepo/releases/tag/v1.0)

## Setup (for Claude)
1. Store and unzip the **Wwise-MCP** `.zip` file at your desired location.
2. Launch the **Claude Desktop** application.
3. Open **File → Settings**:
> <img src="https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/images/setup/Claude/ClaudeSetup_01.png" alt="ClaudeSetup_01" width="500">
4. Go to **Developer → Edit config**.
> <img src="https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/images/setup/Claude/ClaudeSetup_02.png" alt="ClaudeSetup_02" width="500">
6. This will open the `claude_desktop_config.json` file in your default editor.
7. Paste the Wwise-MCP tool configuration snippet into the appropriate section of the config json file. Make sure to set the path to where your Wwise-MCP lives.
   ```bash
   {
       "mcpServers":
       {
            "wwise-mcp":
            {
              "command": "C:\\Your\\PathTo\\Wwise-MCP.exe",
              "args": []
            }
       }
   }
    ```
9. Save the file and restart Claude Desktop for the updated JSON to take effect.
> <img src="https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/images/setup/Claude/ClaudeSetup_03.png" alt="ClaudeSetup_03" width="500">
