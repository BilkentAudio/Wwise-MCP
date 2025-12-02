<p align="center">
  <img src="images/wwise_mcp_logo.png" alt="wwise_mcp_logo" width="300">
</p>

<div align="center">
  
# Model Context Protocol for Wwise

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Wwise](https://img.shields.io/badge/Wwise%20-v2024.1%2B-blue.svg)](https://www.audiokinetic.com/en/wwise/)
[![GitHub release](https://img.shields.io/github/v/release/bilkentaudiodev/Wwise-MCP)](https://github.com/bilkentaudiodev/Wwise-MCP/releases)
[![Status](https://img.shields.io/badge/Status-Experimental-red)]()

</div>

# Wwise-MCP
Wwise-MCP is a Model Context Protocol server that allows LLMs to interact with Wwise Authorng. It exposes tools from a custom python waapi function library to MCP clients such as Claude or Cursor.

# ⚠️ Experimental Notice

This project is currently in an **EXPERIMENTAL** state. 
It is still under active development and should not be used with Wwise projects intended for production at the moment. Please keep in mind:
- Breaking changes may occur without warning
- Features may be incomplete or unstable
- Documentation may be outdated or missing
- Production use is not recommended at this time

# Features
- **Wwise Session Connection**: Connects to the active Wwise session so the agent can issue WAAPI commands to the appropriate wwise session.
- **Hierarchy Indexing**: Scans a parent path and builds a path-first index of the subtree for fast lookup and navigation.
- **Object Creation & Organization**: Creates actor-mixers, containers, buses, work units, soundbanks, folders, and more under specified parent paths, and can move or rename them in batches.
- **Event Authoring**: Creates multiple Wwise events in one batch from source objects and parent paths, and lists all existing event names.
- **Game Object Management**: Creates, moves, and unregisters game objects in batches, with full 3D positioning support and a global fallback object.
- **RTPC / Switch / State Setup**: Batch-creates RTPCs, switch groups, switches, state groups, and states, and exposes helpers to list and set them at runtime.
- **Audio Import & Discovery**: Imports folders of audio into Wwise under a target parent, and lists all audio files under a given file-system path.
- **Soundbank Configuration & Build**: Includes selected objects in soundbanks and generates soundbanks for specified platforms and languages using project metadata.
- **Runtime Audio Control**: Posts events with optional delays, sets RTPC ramps, switches and states, moves game objects over time, and stops all sounds in the captured session.
- **Layout & Property Utilities**: Toggles Wwise layouts, sets object properties by path, retrieves the current selection, and lists valid property names and value types.
- Refer to [Tools](https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/docs/tools/README.md) page for detailed explanation of each functionality.
  
# Installation

## Prerequisites
- Install [Claude Desktop](https://www.claude.com/download) or [Cursor](https://cursor.com/download) or any MCP compatible AI platform
- Install [Wwise v2024.1+](https://www.audiokinetic.com/en/download/)
- Install the latest [Wwise-MCP.zip](https://github.com/bilkentaudiodev/Wwise-MCP/releases/tag/v1.0)

## Setup
- Once you have the above 3 components installed, configure your MCP Client's json to include the Wwise-MCP application. 
- Refer to the [setup page](https://github.com/bilkentaudiodev/Wwise-MCP/tree/main/docs/setup) for detailed instructions

# Quickstart

1. **Connect to your Wwise project**  
   Always start by running **“Connect to my Wwise project”**.  
   This attaches Wwise-MCP to your currently open Wwise session.

2. **Let your MCP Client (i.e Claude) “see” your project structure**  
   Use the **“Resolve parent path”** command.  
   This builds an index of objects under a given Wwise path so Claude can cache and navigate your project by paths.
   A good place to begin is one of Wwise’s top-level roots, for example:
   - `\Actor-Mixer Hierarchy`
   - `\Events`
   - `\Switches`, `\States`, `\Game Parameters`
  
   Example prompt:  
   > Resolve all path relationships in actor mixer.

3. Before using any game object–related prompts (e.g. “Post X event on 5 new game objects and spread them around 500 units from the origin”), make sure you’ve enabled “Start Capture” (red when enabled) in Wwise’s Game Object view.
   > <img src="https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/images/quickstart/Quickstart_GameObject.png" alt="Quickstart_GameObject" width="1000">

# Directory Structure

- **docs/** - Documentation
  - **setup/** - Instructions for installing and configuring Wwise-MCP and MCP clients ([Claude](https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/docs/setup/Claude/ClaudeSetup.md) & [Cursor](https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/docs/setup/Cursor/CusorSetup.md))
  - **tools/** - A list of all functionalities and example prompts

- **app/** - Python server and instructions for setting up Python environment can be found in the README
  - **scripts/** - Python application source code 


# Developers
- Wwise-MCP consists of three Python modules.
- The main entry point is wwise_mcp.py.
- Be sure you are using python version 3.13+
- More info can be found [here](https://github.com/bilkentaudiodev/Wwise-MCP/blob/main/app/README.md)

# License
Apache 
# Feedback/Questions
Feel free to reach out to me at bilkentaudiodev@gmail.com
