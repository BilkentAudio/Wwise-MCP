## Tool List

Below is the list of commands exposed by Wwise-MCP, along with example prompts you can give to your MCP client (i.e Claude).

---

### `connect_to_wwise`

**Description**  
Reconnects Wwise-MCP to the currently active Wwise Authoring session.

**Example prompts**

- “Connect to my Wwise project.”
- “Reconnect to the current Wwise session.”
- “Make sure you’re connected to Wwise before doing anything else.”

---

### `resolve_all_path_relationships_in_parent`

**Description**  
Builds a path-first index of all objects under a given parent path (subtree). This lets Claude “see” and navigate the structure of your Wwise project via paths.

**Example prompts**

- “Resolve all path relationships in `\Actor-Mixer Hierarchy`.”
- “Index everything under `\Events` so you can browse my events.”
- “Resolve all path relationships in `\Actor-Mixer Hierarchy\Default Work Unit`.”

---

### `create_objects`

**Description**  
Creates one or more Wwise objects (Actor-Mixers, Buses, Containers, Sounds, Work Units, etc.) given their names, types, and parent paths. If no parent paths are provided, the command can re-use `prev_response_objects` from the last call. 

**Note**: this does not create events as there are more considerations to account for during event creation. Event creation is handled by the `create_events` function (below). 

**Example prompts**

- “Create three child objects called `AM_Footsteps`, `AM_Weapons`, and `AM_Ambience` as ActorMixers under `\Actor-Mixer Hierarchy\Default Work Unit`.”
- “Using the objects returned from the previous call, create a `RandomSequenceContainer` named `UI_Clicks_Random` under each of them.”
- “Create a new bus called `SFX_Master` under `\Master-Mixer Hierarchy\Default Work Unit`.”

---

### `create_blend_tracks`

**Description**  
Creates one or more Blend Tracks inside existing Wwise Blend Containers. If no Blend Container paths are provided, the command can re-use `prev_response_objects` from the last call.

**Note**: this only creates the Blend Track objects themselves. It does not assign a crossfade RTPC or Game Parameter. Those relationships must be configured separately.

**Example prompts**

- “Create two Blend Tracks called `Near` and `Far` inside `\Actor-Mixer Hierarchy\Vehicles\Engine_BlendContainer`.”
- “Using the Blend Containers returned from the previous call, create Blend Tracks named `Idle`, `Cruise`, and `MaxRPM` in each of them.”
- “Create a Blend Track called `Interior` and another called `Exterior` inside `\Actor-Mixer Hierarchy\Ambience\Room_BlendContainer`.”

---

### `create_events`

**Description**  
Creates multiple Wwise Events in one batch from lists of source objects, destination parent paths, event types, and event names.

**Example prompts**

- “Create a `Play` event called `Play_Footsteps_Grass` for `\Actor-Mixer Hierarchy\Characters\Player\Footsteps_Grass` under `\Events\Default Work Unit\Footsteps`.”
- “Create four `Play` events for these sources: [list paths], and put all of them under `\Events\Default Work Unit\Weapons`.”
- “Batch-create ‘Play’ events for all the sounds you just listed and place them under `\Events\Default Work Unit\Imported`.”

---

### `create_game_objects`

**Description**  
Creates multiple game objects at once in the Wwise sound engine, optionally with initial 3D positions. 

**Note**: Ensure **Start Capture** is toggled before using this command.

**Example prompts**

- “Create five game objects named `RainEmitter_01` through `RainEmitter_05` around the origin at random positions within a radius of 10 units.”
- “Create a game object called `Player` at position (0, 0, 0) and another called `Campfire` at (10, 0, 2).”
- “Create three game objects for birds, spaced evenly along the X-axis from -5 to 5 at Y=0, Z=2.”

---

### `create_rtpcs`

**Description**  
Creates RTPCs in one batch under `\Game Parameters`. You can specify names, parent paths, and min/max ranges. If min/max aren’t specified, assume `0.0` to `100.0`.

**Example prompts**

- “Create RTPCs `Player_Health`, `Player_Stamina`, and `Environment_Density` under `\Game Parameters\Gameplay` with a range of 0 to 100.”
- “Create an RTPC named `Music_Intensity` under `\Game Parameters\Music` from 0.0 to 1.0.”
- “Batch-create RTPCs for `WindSpeed` and `RainIntensity` under `\Game Parameters\Weather` with default ranges.”

---

### `create_switch_groups`

**Description**  
Creates switch groups under `\Switches`. The group must exist before creating its switches.

**Example prompts**

- “Create a switch group `Footstep_Surface` under `\Switches\Default Work Unit`.”
- “Create switch groups `Weather_Type` and `TimeOfDay` under `\Switches\Environment`.”
- “Set up a switch group called `Weapon_Type` under `\Switches\Gameplay`.”

---

### `create_switches`

**Description**  
Creates switches under an existing switch group (whose path should start with `\Switches`).

**Example prompts**

- “Under `\Switches\Default Work Unit\Footstep_Surface`, create switches `Grass`, `Dirt`, `Stone`, and `Metal`.”
- “Add switches `Rain`, `Snow`, and `Wind` to the `Weather_Type` switch group.”
- “Create switches `Day`, `Night`, and `Dusk` under the `TimeOfDay` switch group.”

---

### `create_state_groups`

**Description**  
Creates state groups under `\States`. The group must exist before its child states.

**Example prompts**

- “Create a state group called `Game_State` under `\States\Default Work Unit`.”
- “Create state groups `Music_Mode` and `Combat_State` under `\States\Gameplay`.”
- “Add a state group `UI_Focus` under `\States\UI`.”

---

### `create_states`

**Description**  
Creates states under an existing state group (path should start with `\States` and represent the parent state group).

**Example prompts**

- “Under `\States\Default Work Unit\Game_State`, create states `MainMenu`, `Exploration`, and `Combat`.”
- “Add states `Calm`, `Tension`, and `BossFight` to the `Music_Mode` state group.”
- “Under `\States\UI\UI_Focus`, create states `Inventory`, `Map`, and `Dialogue`.”

---

### `move_object_by_path`

**Description**  
Moves a Wwise object from one path to another parent path. All child objects move with it.

**Example prompts**

- “Move `\Actor-Mixer Hierarchy\Default Work Unit\Temp` to `\Actor-Mixer Hierarchy\Default Work Unit\Archive`.”
- “Move the sound `\Actor-Mixer Hierarchy\SFX\Footsteps\Footstep_Stone` to `\Actor-Mixer Hierarchy\SFX\Footsteps\Legacy`.”
- “Re-parent all assets under `\Events\Old` to be under `\Events\Default Work Unit\Deprecated`.”

---

### `rename_objects`

**Description**  
Renames one or more Wwise objects, either by providing their paths or by using the most recent `prev_response_objects`.

**Example prompts**

- “Rename `\Actor-Mixer Hierarchy\Default Work Unit\AM_Temp` to `AM_Environment`.”
- “For the objects you just created, append `_Test` to each of their names.”
- “Rename these paths [list] to [new names] accordingly.”

---

### `get_objects_info`

**Description**  
Retrieves detailed information about one or more Wwise objects by path. You can request standard WAAPI fields (such as `id`, `name`, `type`, `path`, `parent`, `children`, and `notes`) as well as custom properties and references using Wwise's `@` and `@@` syntax.

- `@PropertyName` returns the value authored directly on the object.
- `@@PropertyName` returns the fully resolved value after inheritance and override resolution.

For example, if a Random Container inherits its Output Bus from a parent Actor-Mixer, `@OutputBus` may be empty while `@@OutputBus` returns the inherited bus.

**Example prompts**

- “Get the name, type, path, and notes for `\Actor-Mixer Hierarchy\Weapons\Rifle_Fire`.”
- “Show me `@Volume`, `@Pitch`, and `@@OutputBus` for `\Actor-Mixer Hierarchy\Characters\Player\Footsteps`.”
- “Retrieve the children, attenuation, output bus, and effects for all objects returned from the previous call.”
- “Compare authored versus resolved Output Bus values for `\Actor-Mixer Hierarchy\UI\Button_Click`.”

---

### `get_property_and_reference_names`

**Description**  
Retrieves all valid WAAPI properties and references available for a Wwise object. This is useful when determining which `@Property` and `@@Property` fields can be queried or modified for a specific object type.

**Example prompts**

- “Show me all available properties and references for `\Actor-Mixer Hierarchy\Weapons\Rifle_Fire`.”
- “What fields can I query on this Blend Container?”
- “List every property available on `\Master-Mixer Hierarchy\Default Work Unit\SFX`.”
- “Before modifying this object, show me all supported `@` and `@@` fields.”

---

### `get_music_transitions`

**Description**  
Retrieves all Music Transition rules authored inside a Music Switch Container, Music Playlist Container, Music Segment, or other music object. This is useful for inspecting transition logic, synchronization settings, fade behavior, transition segments, source/destination contexts, and cue-based navigation.

**Example prompts**

- “Show me all transition rules in `\Interactive Music Hierarchy\Combat_System`.”
- “Inspect the music transitions inside `\Interactive Music Hierarchy\Explore_to_Combat`.”
- “List all transition segments, fade durations, and sync settings for this Music Switch Container.”
- “Show me which transitions use transition segments and which are direct jumps.”
- “Retrieve all music transitions under `\Interactive Music Hierarchy\Default Work Unit\BattleMusic`.”

---

### `import_audio_files`

**Description**  
Imports all audio files under a given file system folder (e.g. `C:\Audio`) into a specified Wwise parent object or path.

**Example prompts**

- “Import all audio files under `C:\GameAudio\Footsteps\Grass` into `\Actor-Mixer Hierarchy\Default Work Unit\Footsteps\Grass`.”
- **Note**: You do not have to specify the destination path if Wwise-MCP already resolved path relationships for that given path. "Import all audio files under `C:\GameAudio\Footsteps\Grass` into Grass container in footstesps under actor mixer."

---

### `list_all_event_names`

**Description**  
Lists the names of all events in the Wwise project.

**Example prompts**

- “List all event names in this project.”
- “Show me all existing Wwise events.”
- “Print a list of all events so we can reuse them instead of creating new ones.”

---

### `list_all_rtpc_names`

**Description**  
Lists the names of all RTPCs in the Wwise project.

**Example prompts**

- “List all RTPC names.”
- “Show me every RTPC currently defined in the project.”
- “List all RTPCs so I can decide which one to use for player health.”

---

### `list_all_switchgroups_and_switches`

**Description**  
Lists all switch groups and their switches, grouped in a dictionary-like structure.

**Example prompts**

- “List all switch groups and their switches.”
- “Show me a mapping of every switch group to its switches.”
- “Print all switch groups and the switches they contain.”

---

### `list_all_stategroups_and_states`

**Description**  
Lists all state groups and their states, grouped in a dictionary-like structure.

**Example prompts**

- “List all state groups and their states.”
- “Show me all state groups with the states inside each.”
- “Print a mapping of state groups to states.”

---

### `list_all_game_objects_in_wwise`

**Description**  
Lists all game objects currently registered in the Wwise session.

**Example prompts**

- “List all game objects in the current Wwise session.”
- “Show me all active game objects so I know what I can post events on.”
- “Print all registered game objects and their IDs.”

---

### `run_waql`

**Description**  
Executes a raw WAQL query against the Wwise project and returns all matching objects. This is the most flexible query tool and can be used for ad-hoc project exploration, hierarchy traversal, reference lookups, filtering, and object discovery.

Custom return fields may be specified, including Wwise properties and references using the same `@Property` and `@@Property` syntax supported by `get_objects_info`. If no return fields are provided, the command returns `id`, `name`, `type`, and `path`.

**Example prompts**

- “Run the WAQL query `$ "\\Actor-Mixer Hierarchy" select descendants`.”
- “Find all Random Containers in the project using WAQL.”
- “Run a WAQL query to find every Sound object whose name contains `Footstep`.”
- “Show all objects that reference `\Game Parameters\Default Work Unit\Speed`.”
- “Execute this WAQL query and return each object's name, path, and `@@OutputBus`.”

---

### `find_references_to`

**Description**  
Finds every object in the project that references a given object. This is the quickest way to answer questions such as “What uses this object?” or “What will be affected if I modify or delete this?”

The target object may be specified using a project path, GUID, or qualified object name. This tool can identify references from RTPCs, Blend Tracks, Attenuations, Output Buses, Auxiliary Sends, Switches, States, Effects, and other Wwise relationships.

**Example prompts**

- “Find everything that references `\Game Parameters\Default Work Unit\Speed`.”
- “What currently uses the `Player_Health` Game Parameter?”
- “Show all objects that reference `\Master-Mixer Hierarchy\Default Work Unit\SFX_Bus`.”
- “Find every object using the `Explosion_Reverb` ShareSet.”
- “Before I delete this Attenuation object, show me everything that references it.”

---

### `post_event`

**Description**  
Posts a Wwise event by name on a specified game object after an optional delay (milliseconds).  
If no game object is given, it posts to the global `Global` game object. If the game object doesn’t exist, it is created automatically.

**Arguments**

- `event_name: str` — Wwise event name to post.
- `game_obj_name: str` — Target game object name (use `"Global"` for 2D / ambience events).
- `delay_ms: int` — Delay before the soundengine posts the event. `0` means post immediately.
- `wait: bool = False` — Reply mode. `False` (default) fire-and-forget: returns as soon as the dispatcher enqueues the call. `True` synchronous: blocks on the WAAPI reply queue, which is useful for serializing a batch of posts. When combined with `delay_ms > 0`, the reply timeout is auto-extended to cover the scheduled future dispatch, so delayed synchronous posts do not spuriously time out.

**Example prompts**

- “Post the `Play_Ambience_Forest` event on the `Global` game object immediately.”
- “Post `Play_Footsteps_Grass` on the `Player` game object with a delay of 500 ms.”
- “Trigger `Stop_All_Music` on `Global` right now.”
- “Post `Play_Stinger` on `Global` and wait for the WAAPI reply before issuing the next event (`wait=True`).”

---

### `set_rtpc`

**Description**  
Sets an RTPC value on a game object over a duration (in ms), from a start value to an end value.  
If no game object is given, applies the RTPC to the `Global` game object.

**Example prompts**

- “Set the RTPC `Music_Intensity` from 0 to 100 over 10 seconds on `Global`.”
- “Ramp `WindSpeed` from 20 to 80 over 5 seconds on the `Player` game object.”
- “Set `Player_Health` RTPC to 25 instantly on `Player`.”

---

### `set_state`

**Description**  
Sets a state by specifying the state group and state names.

**Example prompts**

- “Set `Game_State` to `Exploration`.”
- “Switch `Music_Mode` to `BossFight`.”
- “Set the state group `UI_Focus` to `Inventory`.”

---

### `set_switch`

**Description**  
Sets a switch by specifying the switch group and switch names, usually on a given game object.

**Example prompts**

- “On `Player`, set the switch `Footstep_Surface` to `Grass`.”
- “Set `Weather_Type` to `Rain` on `Global`.”
- “Change `TimeOfDay` to `Night` for the `Player` game object.”

---

### `move_game_obj`

**Description**  
Moves a game object from a start position to an end position over a duration (ms).  
If the game object doesn’t exist, it will be created.

**Example prompts**

- “Move the `Player` game object from (0, 0, 0) to (10, 0, 0) over 3 seconds.”
- “Animate `Drone_01` from (0, 5, 2) to (20, 5, 2) across 10 seconds.”
- “Create a `TempSource` game object at (0, 0, 2) and move it to (0, 0, 20) over 5 seconds.”

---

### `stop_all_sounds`

**Description**  
Stops all sounds on all game objects in the captured session.

**Example prompts**

- “Stop all sounds currently playing.”
- “Immediately silence everything in this Wwise session.”
- “Stop all audio on all game objects.”

---

### `include_in_soundbank`

**Description**  
Includes specified objects (events, work units, folders, etc.) into one or more soundbanks by path. An optional `filter` selects which inclusion types (`events`, `structures`, `media`) are written; when omitted it defaults to `["events", "structures"]` (the previous fixed behaviour).

**Example prompts**

- “Include `\Events\Default Work Unit\Footsteps` in the soundbank `\SoundBanks\Default Work Unit\Footsteps_SoundBank`.”
- “Add all events under `\Events\Weapons` to `\SoundBanks\Default Work Unit\Weapons_SB`.”
- “Include these event paths [list] in the `MainGame` soundbank.”
- “Include `\Events\Default Work Unit\Music` in `\SoundBanks\Default Work Unit\Music_SB` with media baked in (`filter=['events','structures','media']`).”

---

### `generate_soundbanks`

**Description**  
Generates soundbanks given lists of soundbank names, target platforms, and languages.  
If unsure, you can use `Windows` and `English(US)`, or call `get_project_info` to discover valid platforms and languages.

**Example prompts**

- “Generate the `MainGame` soundbank for platform `Windows` and language `English(US)`.”
- “Generate soundbanks `Footsteps_SB` and `Weapons_SB` for `Windows` and `English(US)`.”
- “Rebuild all soundbanks we’ve just included objects into for `Windows` / `English(US)`.”

---

### `get_project_info`

**Description**  
Retrieves Wwise project metadata, including available platforms and languages.

**Example prompts**

- “Get project info so we can see which platforms and languages are available.”
- “List all platforms and languages configured in this Wwise project.”
- “Show me the project metadata, including active platforms.”

---

### `get_all_audio_files_at_path_on_file_explorer`

**Description**  
Lists all audio files under a given folder in the file system (e.g. `C:\Audio`).

**Example prompts**

- “List all audio files under `C:\GameAudio\Imports`.”
- “Show me all WAV files inside `/Users/Me/Audio/Footsteps`.”
- “Gather all audio file paths under `D:\SFX\Weapons` so we can import them.”

---

### `set_object`

**Description**  
Low-level wrapper around `ak.wwise.core.object.set` for modifying complex Wwise object fields that cannot be handled by `setProperty` or `setReference`.

This tool is primarily intended for advanced workflows. When a dedicated wrapper exists (such as `assign_music_arguments`, `assign_music_entries`, or `set_playlist_root`), that wrapper should be preferred instead.

Depending on the target field, values may be provided as a single path, a list of paths, or a list of WAAPI schema dictionaries.

**Example prompts**

- “Set the `Arguments` field on this Music Switch Container using these State Groups.”
- “Populate a custom object list field using the following WAAPI schema objects.”
- “Assign these references to the object's complex list field.”
- “Use `set_object` to update a field that does not have a dedicated wrapper.”

---

### `assign_music_arguments`

**Description**  
Assigns one or more State Groups or Switch Groups as Arguments on a Music Switch Container. These Arguments determine which Switches or States the container evaluates when selecting which child object to play.

This must be configured before assigning music entries, as entries depend on the Argument definitions.

**Example prompts**

- “Assign the `Combat_State` State Group as an argument on `\Interactive Music Hierarchy\Combat_System`.”
- “Configure `Combat_State` and `Turn_Switch` as arguments for this Music Switch Container.”
- “Set up the State and Switch Groups this Music Switch Container should evaluate.”
- “Add `Game_State` as the controlling argument for this music container.”

---

### `assign_music_entries`

**Description**  
Assigns State/Switch-to-child mappings on a Music Switch Container. Each entry tells Wwise which child Music Playlist Container, Music Segment, or nested Music Switch Container should play when a specific State or Switch combination is active.

Requires Arguments to have been assigned first using `assign_music_arguments`.

**Example prompts**

- “Map `Combat_State\Explore` to `Explore_Playlist`.”
- “Assign `Combat_State\Combat` to `Combat_Playlist` and `Combat_State\Victory` to `Victory_Segment`.”
- “For the container we just created, assign all child playlists to their corresponding States.”
- “Map the combination of `Combat_State\Combat` and `Turn_Switch\PlayerTurn` to `PlayerTurn_Playlist`.”

---

### `set_playlist_root`

**Description**  
Populates a Music Playlist Container's playlist structure. This tool can create playlists containing Music Segments, nested groups, loop counts, and hierarchical playlist layouts.

Any existing playlist content is replaced.

**Example prompts**

- “Create a playlist containing `Intro_Segment`, `Loop_Segment`, and `Outro_Segment`.”
- “Set the playlist root for `Combat_Playlist` to play `Combat_Loop` infinitely.”
- “Create a playlist group containing three random combat segments.”
- “Replace the current playlist with this new hierarchy of Music Playlist Items.”

---

### `set_rtpc_curve`

**Description**  
Creates or updates an RTPC curve by binding a Control Input (Game Parameter, Modulator, or MIDI source) to a target property on a Wwise object.

Supports custom breakpoint arrays and curve interpolation shapes. This is distinct from attenuation curves, which are handled separately.

**Example prompts**

- “Bind the `Speed` Game Parameter to `Volume` on `Engine_Loop`.”
- “Create an RTPC curve that drives Pitch from the `RPM` Game Parameter.”
- “Set an RTPC curve on an Effect property using these breakpoints.”
- “Map `Player_Health` to Lowpass with a smooth S-curve response.”

---

### `set_object_reference`

**Description**  
Assigns a Wwise object reference to another Wwise object. Common examples include setting an Output Bus, Attenuation, Conversion Settings, ShareSet, or other reference-based relationships.

**Example prompts**

- “Assign `\Attenuations\Footstep_Attenuation` to `Footstep_Grass`.”
- “Set the Output Bus of `Explosion_Large` to `\Master-Mixer Hierarchy\SFX_Bus`.”
- “Assign the `Hall_Reverb` ShareSet to this Auxiliary Bus.”
- “Update the object's Attenuation reference to use `Weapon_Attenuation`.”

---

### `set_object_property`

**Description**  
Sets a property value on a Wwise object given its path and property name. The value can be an int, bool, or string (depending on the property).

**Example prompts**

- “Set the `Volume` property of `\Actor-Mixer Hierarchy\SFX\Footsteps\Footstep_Stone` to -3 dB.”
- “Turn `Mute` on for `\Actor-Mixer Hierarchy\SFX\Ambience\City`.”
- “Set the `IsGlobal` property of this RTPC to `True`.”

---

### `set_object_randomizer`

**Description**  
Enables, disables, or modifies a property randomizer on a Wwise object. Randomizers are commonly used to introduce variation in properties such as Volume, Pitch, Lowpass, and Highpass to reduce repetition during playback.

**Example prompts**

- “Add a Pitch randomizer between -50 and 50 cents on `Footstep_Grass`.”
- “Enable Volume randomization on all footstep sounds.”
- “Disable the Pitch randomizer on `Weapon_Reload`.”
- “Set a randomizer on `Lowpass` with a range of -10 to 10.”

---

### `set_attenuation_curve`

**Description**  
Creates or updates an attenuation curve on a Wwise Attenuation object. Supports all attenuation curve types including volume, filtering, spread, focus, obstruction, occlusion, diffraction, and transmission.

Custom curves can be authored using breakpoint arrays and interpolation shapes.

**Note**: `RadiusMax` must already be configured on the Attenuation object. Curve points must begin at `0.0` and end at `RadiusMax`.

**Example prompts**

- “Create a custom volume attenuation curve on `Footstep_Attenuation`.”
- “Set the Low Pass Filter attenuation curve for `Weapon_Attenuation`.”
- “Make the volume attenuation fall off gradually until 20 meters.”
- “Configure an occlusion LPF curve using these breakpoint values.”
- “Replace the existing Spread curve on this Attenuation object.”

---

### `assign_switch_container_child`

**Description**  
Assigns a child object to a specific Switch within a Switch Container. This defines which object should play when the corresponding Switch is active.

Typically used to map Sounds, Random Containers, Blend Containers, or Actor-Mixers to Switch values.

**Example prompts**

- “Assign `Footstep_Grass` to the `Grass` Switch.”
- “Map `Footstep_Concrete_Random` to `\Switches\SurfaceType\Concrete`.”
- “Assign each child container to its matching Surface Type Switch.”
- “Connect this Random Container to the `Indoor` Switch state.”

---

### `assign_blend_track_child`

**Description**  
Assigns a child object to an existing Blend Track and optionally configures crossfade boundaries and curve shapes.

Blend Tracks themselves are not path-addressable in Wwise, so this command requires the Blend Track GUID returned by `create_blend_tracks`.

For crossfading, the Blend Track should have `EnableCrossFading` enabled and a Game Parameter assigned as its `LayerCrossFadeControlInput`.

**Example prompts**

- “Assign `Engine_Idle` to the `Idle` Blend Track.”
- “Add `Engine_HighRPM` to this Blend Track and configure crossfade edges.”
- “Assign these engine layers to their corresponding Blend Tracks.”
- “Set up a crossfade between `Engine_Low`, `Engine_Mid`, and `Engine_High` using the RPM Game Parameter.”

---

### `assign_child_to_random_sequence_playlist`

**Description**  
Assigns child objects to the playlist of a Random Container or Sequence Container.

The playlist can either be completely replaced or appended to. All referenced child objects must already exist under the Random or Sequence Container hierarchy.

**Example prompts**

- “Add all footstep variations to `Footstep_Grass_Random`.”
- “Replace the playlist in `Weapon_Fire_Random` with these sounds.”
- “Append these three new variations to the existing Random Container playlist.”
- “Populate the Sequence Container with the intro, loop, and outro sounds in order.”

---

### `retrieve_selected_objs`

**Description**  
Retrieves whatever objects are currently selected in the Wwise Authoring UI.

**Example prompts**

- “Get the currently selected objects in Wwise.”
- “Use the objects I have selected in Wwise as the target for the next operation.”
- “Retrieve the selected objects and show me their paths.”

---

### `unregister_gameobject`

**Description**  
Unregisters (removes) a game object from the Wwise sound engine by name.

**Example prompts**

- “Unregister the `TempEmitter` game object.”
- “Remove all temporary debug game objects with names starting with `Debug_`.”
- “Unregister `RainEmitter_01` from the current session.”

---

### `toggle_layout`

**Description**  
Switches the current Wwise layout to a requested layout.  
Valid layouts: `Designer`, `Profiler`, `Soundbank`, `Mixer`, `Audio Object Profiler`, `Voice Profiler`, `Game Object Profiler`.

**Example prompts**

- “Switch Wwise to the `Profiler` layout.”
- “Toggle the layout to `Game Object Profiler` so I can inspect my game objects.”
- “Change to the `Soundbank` layout.”

---

### `get_all_property_name_and_valid_value_types`

**Description**  
Returns a help string listing WAAPI property identifiers and valid value types for a given Wwise object type.

**Example prompts**

- “Show me all valid property names and types for a Sound object.”
- “List the WAAPI properties and valid value types for an Event.”
- “Give me a reference of all properties I can set on a Bus.”

---

### `delete_object`

**Description**  
Deletes a Wwise object using its GUID, project path, or qualified object name. Use with caution, as deleting an object may affect any references, RTPCs, buses, switch assignments, playlists, or other systems that depend on it.

Consider using `find_references_to` before deletion to identify affected objects.

**Example prompts**

- “Delete `\Actor-Mixer Hierarchy\Unused\Old_Footstep_Sound`.”
- “Remove the ShareSet called `Legacy_Reverb`.”
- “Delete this object using its GUID.”
- “Find everything referencing this object, then delete it.”

---

## Remote Connection Tools

### `remote_get_connection_status`

**Description**  
Retrieves the current Wwise Authoring ↔ Sound Engine remote connection status.

This is useful for determining whether Authoring is connected to a running game, console, or profiler capture before using runtime or profiler-related tools.

**Note**: Requires a Wwise Authoring instance running with a UI. Not supported by headless WwiseConsole WAAPI servers.

**Example prompts**

- “Check whether Wwise is connected to the game.”
- “Show the current remote connection status.”
- “Verify that Authoring is connected before starting a profiler capture.”
- “Which Sound Engine instance is currently connected?”

---

### `remote_get_available_consoles`

**Description**  
Lists all available Sound Engine instances that Wwise Authoring can connect to.

Useful when multiple local, remote, or console builds are running and you need to select a specific target.

**Note**: Requires a Wwise Authoring instance running with a UI.

**Example prompts**

- “List all available game instances I can connect to.”
- “Show all Sound Engine targets discovered by Wwise.”
- “Find the running game instance on localhost.”
- “What consoles are available for remote connection?”

---

### `remote_connect`

**Description**  
Connects Wwise Authoring to a running Sound Engine instance or an existing `.prof` profiler capture.

Supports local targets, remote targets, and saved profiler captures.

**Note**: Requires a Wwise Authoring instance running with a UI.

**Example prompts**

- “Connect Wwise to the game running on localhost.”
- “Connect to the available Xbox instance.”
- “Attach Authoring to the game running on this machine.”
- “Open and connect to this `.prof` capture file.”

---

### `remote_disconnect`

**Description**  
Disconnects Wwise Authoring from the currently connected Sound Engine instance.

This only affects the Authoring remote connection and does not disconnect the WAAPI session itself.

**Example prompts**

- “Disconnect Wwise from the game.”
- “Close the current remote connection.”
- “Detach Authoring from the Sound Engine.”
- “Stop monitoring the connected runtime instance.”

---

## Effects & Plug-ins

### `create_effect_share_set`

**Description**  
Creates a Custom Effect or Effect ShareSet under the specified parent path and optionally initializes plug-in properties.

Useful for automating effect setup and reusable effect chains.

**Example prompts**

- “Create a new Reverb ShareSet called `Large_Hall`.”
- “Create a Steam Audio Reflection ShareSet under `\Effects\Default Work Unit`.”
- “Create an Effect ShareSet and initialize its properties.”
- “Create a custom effect preset for weapon tails.”

---

### `add_effect_to_object`

**Description**  
Adds an Effect or ShareSet reference to a Sound, Actor-Mixer, or Bus.

Effects can be appended to the existing chain or replace the current effect list entirely.

**Example prompts**

- “Add the `Large_Hall` Reverb ShareSet to `Explosion_Large`.”
- “Insert this effect onto the SFX bus.”
- “Append a Compressor to the existing effect chain.”
- “Replace all effects on this bus with these ShareSets.”

---

### `set_plugin_property`

**Description**  
Sets a plug-in-specific property using WAAPI's object-set workflow.

Useful for configuring effect parameters that older property-setting APIs cannot modify, including many third-party plug-ins and advanced Wwise effects.

**Example prompts**

- “Set the Reflection Amount property on this Steam Audio effect.”
- “Update the Reverb Time parameter to 3.5 seconds.”
- “Configure Occlusion on this plug-in.”
- “Set the plug-in property `Transmission` to enabled.”

---

### `create_source_plugin`

**Description**  
Creates a Source Plug-in as a child of a Sound or Voice object.

Useful for procedural generators, diagnostic signals, synthesis workflows, and SoundSeed-based systems.

**Example prompts**

- “Create a Sine source under this Sound object.”
- “Add a Tone Generator source for testing.”
- “Create a SoundSeed Air source and configure its properties.”
- “Generate a Silence source for debugging playback behavior.”

---

## Profiler Tools

### `profiler_start_capture`

**Description**  
Starts a Wwise Profiler capture.

Typically used before gathering voice, RTPC, bus, meter, or audio-object information.

**Example prompts**

- “Start a profiler capture.”
- “Begin recording profiler data.”
- “Start capturing runtime audio information.”
- “Begin a profiling session.”

---

### `profiler_stop_capture`

**Description**  
Stops the active Wwise Profiler capture.

**Example prompts**

- “Stop the profiler capture.”
- “End the current profiling session.”
- “Finish recording profiler data.”
- “Stop capturing runtime information.”

---

### `profiler_get_cursor_time`

**Description**  
Returns the current profiler cursor position in milliseconds.

Supports both the live capture cursor and the user-controlled cursor.

**Example prompts**

- “What time is the profiler cursor currently at?”
- “Show the capture cursor position.”
- “Get the user cursor time.”
- “Return the current profiler timestamp.”

---

### `profiler_enable_data`

**Description**  
Enables or disables specific categories of profiler data collection.

Some profiler tools require specific data types to be enabled before information becomes available.

**Important**: Enable `voiceInspector` before using `profiler_get_voice_contributions`.

**Example prompts**

- “Enable voice inspector data.”
- “Enable audio object and bus profiling.”
- “Turn on RTPC and voice capture data.”
- “Configure profiler data collection for voice debugging.”

---

### `profiler_get_voices`

**Description**  
Returns all active voices at a specific profiler capture time.

Useful for debugging virtualization, playback state, priorities, routing, and voice counts.

**Example prompts**

- “Show all active voices.”
- “List every voice playing at the current capture time.”
- “Find virtualized voices.”
- “Inspect voice activity for this game object.”

---

### `profiler_get_voice_contributions`

**Description**  
Returns the contribution tree for a specific voice, including volume, filtering, and object-level contribution data.

Useful for understanding why a voice sounds the way it does after all routing and processing have been applied.

**Example prompts**

- “Show the contribution tree for this voice.”
- “Why is this voice quieter than expected?”
- “Inspect all volume and filter contributions for this sound.”
- “Analyze the voice processing chain.”

---

### `profiler_get_audio_objects`

**Description**  
Returns Audio Objects present in the post-mix pipeline at a given profiler time.

Useful for inspecting object-based audio, effect processing, metering, and spatialization.

**Example prompts**

- “Show all active audio objects.”
- “Inspect object-based audio processing.”
- “List audio objects on this bus.”
- “Show RMS and peak meter values for active audio objects.”

---

### `profiler_get_busses`

**Description**  
Returns active busses at a given profiler capture time.

Useful for inspecting routing, bus activity, voice counts, downstream gain, and effect usage.

**Example prompts**

- “Show all active busses.”
- “Inspect the bus routing hierarchy.”
- “List voice counts per bus.”
- “Find which busses currently have active effects.”

---

### `profiler_get_rtpcs`

**Description**  
Returns all active RTPC values at a given profiler capture time.

Useful for validating runtime parameter behavior and troubleshooting game parameter updates.

**Example prompts**

- “Show all active RTPCs.”
- “Inspect current Game Parameter values.”
- “What is the current value of the Speed RTPC?”
- “List all RTPCs affecting the running game.”

---

### `profiler_save_capture`

**Description**  
Saves the current profiler capture to a `.prof` file.

Useful for archiving captures, sharing profiling sessions, and offline analysis.

**Example prompts**

- “Save the current profiler capture.”
- “Export this profiling session to a `.prof` file.”
- “Write the capture to disk.”
- “Save the profiler recording for later analysis.”

---
