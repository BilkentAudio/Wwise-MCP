# Installation

## Prerequisites
- Install [Cursor](https://cursor.com/download)
- Install [Wwise v2024.1+](https://www.audiokinetic.com/en/download/)
- Install [Wwise-MCP](https://github.com/t90786613/TestRepo/releases/tag/v1.0)

## Setup (for Cursor)
1. Store and unzip the **Wwise-MCP** `.zip` file at your desired location.
2. Launch the **Cursor Desktop** application.
3. Open **Settings** icon the upper right of the application:
> <img src="https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/images/setup/Cursor/Cursor_Setup_01.png" alt="CursorSetup_01" width="1000">
4. Go to **Tools & MCP → Add Custom MCP**.
> <img src="https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/images/setup/Cursor/Cursor_Setup_02.png" alt="Cursor_Setup_02" width="1000">
6. This will open the `mcp.json` file in your editor.
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
> <img src="https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/images/setup/Cursor/Cursor_Setup_03.png" alt="Cursor_Setup_03" width="500">
8. Save the file
9. If everything works, Wwise-MCP should be visible under **Installed MCPs** and appear **green**.
10. Start chatting!
> <img src= "https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/images/setup/Cursor/Cursor_Setup_04.png" alt="ClaudeSetup_04" width="1250">
11. When chatting you can toggle between different agents via the button shown below. I had some success with Grok Code.
> <img src= "https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/images/setup/Cursor/Cursor_Setup_05.png" alt="ClaudeSetup_05" width="1000">
