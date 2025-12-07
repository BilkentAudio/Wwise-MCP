from dataclasses import dataclass
from fastmcp import FastMCP
import asyncio
import anyio
import wwise_python_lib as WwisePythonLibrary
import inspect
import ast
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)

def get_log_dir() -> Path:
    if getattr(sys, "frozen", False):  # running as bundled exe
        return Path(sys.executable).resolve().parent
    else:
        return Path(__file__).resolve().parent # running from source

def configure_logger(): 
    log_path = get_log_dir() / "WwiseMCP.log"   # log path 

    handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(name)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
        handlers=[handler],
    )

def create_asyncio_loop(): # needed when connecting to waapi client
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop

def connect_to_wwise() -> None:
    loop = create_asyncio_loop()
    try: 
        WwisePythonLibrary.connect_to_waapi()
    except Exception: 
        logger.exception("Failed to connect to Wwise Client.")
        raise 
    finally:
        loop.close()

def resolve_all_path_relationships_in(parent_path: str) -> list[dict]: 
    if not parent_path: 
        raise ValueError("Please provide a non empty parent path to resolve descendant paths in.")
    
    try:
        nodes = WwisePythonLibrary.fetch_nodes(parent_path)

        result : list[dict] = []
        for node in nodes:
            result.append(WwisePythonLibrary.get_fields_from_objects([node["id"]], ["path"]))
        
        return result 
    
    except Exception: 
        logger.exception("Resolve failed for %r", parent_path)
        raise 

def create_child_objects(
    child_names: list[str],
    child_types: list[str],
    parent_paths: list[str], 
    *, 
    prev_response_objects: list[any] | None = None
) -> list[dict]:
    
    objects : list[dict] = prev_response_objects 
    if not objects: 
        objects = [WwisePythonLibrary.get_object_at_path(parent_path) for parent_path in parent_paths]
    
    if not objects: 
        raise ValueError("Both prev_response_objects and parent_paths are empty. Please specify values for at least one of these variables.")

    try:
        try:
            parent_ids = [p["id"] for p in objects]
        except (KeyError, TypeError) as e:
            raise ValueError("One or more parent objects are missing an 'id' field.") from e

        result : list[dict] = []
        for parent_id, child_name, child_type in zip(parent_ids, child_names, child_types):
            result.extend(WwisePythonLibrary.create_object(parent_id, child_name, child_type))

        return result
    
    except Exception: 
        logger.exception("Failed to create objects.")
        raise 
    
def create_events(
    source_paths: list[str], 
    dst_parent_paths: list[str], 
    event_types: list[str], 
    event_names: list[str]
) -> list[dict]: 
    
    if not (len(dst_parent_paths) == len(event_types) == len(event_names) == len(source_paths)):
        raise ValueError(f"All input lists must have the same length when creating events.")
    
    try:         
        results: list[dict] = []

        for src, dst, etype, name in zip(source_paths, dst_parent_paths, event_types, event_names):
            result = WwisePythonLibrary.create_event(src,dst,etype,name)
            results.append(result)

        return results
    
    except Exception: 
        logger.exception("Failed to create events.")
        raise 

def create_game_objects(
    game_obj_names: list[str], 
    positions: list[tuple[float,float,float]]
) -> list[dict]: 
    
    try: 
        zipped = zip(game_obj_names, positions, strict=True)
        results: list[dict] = []

        for game_obj_name, position in zipped:
            result = WwisePythonLibrary.create_game_obj(game_obj_name, position)
            results.append(result)

        return results
    
    except Exception: 
        logger.exception("Failed to create game objects.")
        raise 

def create_rtpcs(
    rtpc_names : list[str], 
    parent_paths : list[str], 
    min_value : list[float], 
    max_value : list[float]
) -> list[dict]:
    
    try: 
        zipped = zip(rtpc_names, parent_paths, min_value, max_value, strict= True)
        results : list[dict] = []

        for rtpc_name, parent_path, min_value, max_value in zipped:
            if min_value > max_value:
                logger.exception("Invalid rtpc ranges for %r ", rtpc_name) 
                raise ValueError(f"Invalid rtpc ranges for {rtpc_name}")
            
            results.append(WwisePythonLibrary.create_rtpc(rtpc_name, parent_path, min_value, max_value))
        
        return results
    
    except Exception: 
        logger.exception("Failed to create rtpcs.")
        raise

def create_switch_groups(
    names: list[str], 
    parent_paths: list[str]
) -> list[dict]:
    
    try: 
        return create_switch_or_state_types(names, parent_paths, "SwitchGroup")
    
    except Exception: 
        logger.exception("Failed to create switch groups.")
        raise
    
def create_switches(
    names: list[str], 
    parent_paths: list[str]
)->list[dict]:
    
    try: 
       return create_switch_or_state_types(names, parent_paths, "Switch")
    
    except Exception: 
        logger.exception("Failed to create switches.")
        raise

def create_state_groups(
    names: list[str], 
    parent_paths: list[str]
)->list[dict]:
    
    try: 
        return create_switch_or_state_types(names, parent_paths, "StateGroup")
    
    except Exception: 
        logger.exception("Failed to create state groups.")
        raise

def create_states(
    names: list[str], 
    parent_paths: list[str]
)->list[dict]:
    
    try: 
        return create_switch_or_state_types(names, parent_paths, "State")
    
    except Exception: 
        logger.exception("Failed to create states.")
        raise

def create_switch_or_state_types(
    names: list[str], 
    parent_paths: list[str], 
    type: str
)->list[dict]:
    
    try: 
        if not (len(parent_paths) == len(names)):
            raise ValueError(f"Length mismatch: names={len(names)} parent_paths={len(parent_paths)}") 
        
        results : list[dict] = []
        
        for name, parent in zip(names, parent_paths):
            results.append(WwisePythonLibrary.create_switch_or_state_types(name,parent, type))

        return results
    
    except Exception: 
        logger.exception("Failed to create switch or state types.")
        raise
    
def move_object_by_path(
    source_path: str, 
    destination_parent_path: str
) -> dict: 
    
    if not source_path: 
        raise ValueError("Pass in a non empty source_path for 'move_object_by_path'.")
    
    if not destination_parent_path: 
        raise ValueError("Pass in a non empty destination_parent_path for 'move_object_by_path'.")

    try: 
        return WwisePythonLibrary.move_object_by_path(source_path, destination_parent_path)
    
    except Exception: 
        logger.exception("Failed to move object from %r to %r", source_path, destination_parent_path)
        raise

def rename_objects(
    paths_of_objects_to_rename: list[str] | None, 
    prev_response_objects: list[any] | None, 
    names: list[str]
) -> list[str]:
        
    try:
        if not names: 
            raise ValueError("Pass a non empty list of names for renaming")
        
        objects : list[dict] = []
        if paths_of_objects_to_rename is not None : 
            objects = [WwisePythonLibrary.get_object_at_path(obj_path) for obj_path in paths_of_objects_to_rename]
        else: 
            objects = prev_response_objects

        if not objects:
            raise ValueError("Pass in either the paths of the objects to be renamed or include the 'prev_response_objects='$last''to use results from a previous function call") 
        
        objects = [o for o in objects if o] 
        if not objects:
            raise ValueError("No valid objects resolved to rename.")

        if len(objects) != len(names):
            raise ValueError(
            f"Length mismatch: objects={len(objects)} names={len(names)}"
            )

        return WwisePythonLibrary.rename_objects(objects, names)

    except Exception: 
        logger.exception("Failed to rename objects.")
        raise

def import_audio(
    source_paths: list[str],
    destination_paths: list[str],
) ->list[dict]:
    try:
        if not source_paths: 
            raise ValueError("Specify source_files to import.")
        if not destination_paths:
            raise ValueError ("Specify destination_paths to import audio into")

        return WwisePythonLibrary.import_audio_files(source_paths, destination_paths)
    
    except Exception: 
        logger.exception("Failed to import audio.")
        raise

def list_all_event_names():
    try: 
        return WwisePythonLibrary.list_all_event_names() 
    except Exception: 
        logger.exception("Failed to retrieve event names in wwise project.")
        raise

def list_all_rtpc_names():
    try: 
        return WwisePythonLibrary.list_all_rtpc_names() 
    except Exception: 
        logger.exception("Failed to retrieve rtpc names in wwise project.")
        raise

def list_all_switchgroups_and_switches():
    try: 
        return WwisePythonLibrary.get_all_switchgroups_and_switches_grouped() 
    except Exception: 
        logger.exception("Failed to retrieve switch groups and switches in wwise project.")
        raise

def list_all_stategroups_and_states():
    try: 
        return WwisePythonLibrary.get_all_stategroups_and_states_grouped() 
    except Exception: 
        logger.exception("Failed to retrieve state groups and states in wwise project.")
        raise

def list_all_game_objects(): 
    try:
        return WwisePythonLibrary.get_all_game_objs_in_wwise_session()
    except Exception: 
        logger.exception("Failed to retrieve game objects in wwise project.")
        raise
    
def post_event(
    event_name: str, 
    go_name: str, 
    delay_ms: int
)-> int:
    
    try: 
        if not event_name: 
           raise ValueError("Pass in a non empty event name when posting an event.")
       
        if delay_ms < 0:
            raise ValueError("Delay amount cannot be negative when posting an event.") 

        return WwisePythonLibrary.post_event(event_name, go_name, delay_ms)
    
    except Exception: 
        logger.exception("Failed to post event %r", event_name)
        raise

def set_rtpc(
    game_object_name: str | None, 
    rtpc_name: str, 
    start: float, 
    end: float, 
    duration: int
) -> None:
    
    try: 
        if not rtpc_name: 
            raise ValueError("Please indicate the rtpc name to set.")
        
        if duration < 0:
            raise ValueError("Please indicate a non negative duration for the rtpc interpolation.")
        
        if not game_object_name: 
            WwisePythonLibrary.ramp_rtpc(rtpc_name, start, end, duration)
        else:
            WwisePythonLibrary.ramp_rtpc(rtpc_name, start, end, duration, obj = game_object_name, step_ms=50)
    
    except Exception: 
        logger.exception("Failed to set rtpc %r", rtpc_name)
        raise
    
def set_state(
    state_group: str, 
    state: str, 
    delay_ms: int
)-> None:
    
    if not state: 
        raise ValueError("Pass in a non empty state value when setting state.")
    
    if not state_group: 
        raise ValueError("Pass in a non empty state group when setting state.")
    
    if not isinstance(delay_ms, int) or delay_ms < 0: 
        raise ValueError("Ensure that delay_ms is an integer and non-negative when setting state.")
    
    try: 
        WwisePythonLibrary.set_state(state_group, state, delay_ms)
    
    except Exception: 
        logger.exception("Failed to set state %r in state group %r", state, state_group)
        raise

def set_switch(
    game_object_name: str, 
    switch_group: str, 
    switch: str, 
    delay_ms: int
)-> None:
    
    if not switch_group: 
        raise ValueError("Pass in a non empty switch group when setting switch.")
    
    if not switch: 
        raise ValueError("Pass in a non empty switch when setting switch.")
    
    if not isinstance(delay_ms, int) or delay_ms < 0: 
        raise ValueError("Ensure that delay_ms is an integer and non-negative when setting switch.")

    try:
        if not game_object_name: 
            WwisePythonLibrary.set_switch(switch_group, switch, delay_ms)
        else : 
            WwisePythonLibrary.set_switch(switch_group, switch, delay_ms, obj = game_object_name)
    
    except Exception: 
        logger.exception("Failed to set switch %r", switch)
        raise

def move_game_obj(
    game_obj_name: str, 
    start_pos: tuple[float, float, float], 
    end_pos: tuple[float, float, float], 
    duration_ms: int, 
    delay_ms: int
)-> None:
    
    if not game_obj_name: 
        raise ValueError("Pass in a non empty game object name to move.")
    
    if not isinstance(duration_ms, int) or duration_ms < 0: 
        raise ValueError("Ensure that duration_ms is an integer and non-negative when moving game obj.")
    
    if not isinstance(delay_ms, int) or delay_ms < 0: 
        raise ValueError("Ensure that delay_ms is an integer and non-negative when moving game obj.")
    
    try: 
        return WwisePythonLibrary.start_position_ramp(
            obj = game_obj_name,
            start_pos=start_pos, 
            end_pos=end_pos,
            duration_ms = duration_ms,
            step_ms = 100,
            delay_ms=delay_ms,
            front = (0.0, 1.0, 0.0),  
            top = (0.0, 0.0, 1.0),  
        )
    
    except Exception: 
        logger.exception("Failed to set switch.")
        raise

def stop_all_sounds() -> None:
    try: 
        WwisePythonLibrary.stop_all_sounds()
    
    except Exception: 
        logger.exception("Failed to stop all sounds in wwise.")
        raise
        
def include_in_soundbank(
    include_paths: list[str], 
    soundbank_path: str
) -> list[dict]: 
    
    if not include_paths: 
        raise ValueError("Pass in a non empty list of event paths to be included in the indicated soundbank.")

    for include_path in include_paths: 
        if not include_path: 
            raise ValueError("Ensure all elements inside the include_paths are non empty.")
    
    if not soundbank_path: 
        raise ValueError("Pass in a non empty soundbank path.")

    try: 
        return WwisePythonLibrary.include_in_soundbank(include_paths, soundbank_path)
    except Exception: 
        logger.exception("Failed to include %r paths in soundbank %r", len(include_paths), soundbank_path)
        raise

def generate_soundbanks(
    soundbank_names: list[str], 
    platforms: list[str], 
    languages: list[str]
) -> dict:
    
    if not soundbank_names:
        raise ValueError("Pass in a non empty list of soundbank names to generate.")
    
    for soundbank_name in soundbank_names: 
        if not soundbank_name: 
            raise ValueError("Ensure all soundbank names in the soundbank names list are non empty and valid.")

    if not platforms: 
        raise ValueError("Ensure the platform lists is not empty to generate soundbanks. Include at least one platform.")
    
    for platform in platforms: 
        if not platform: 
            raise ValueError("Ensure all platforms in the platform list are non empty and valid.")

    try: 
        return WwisePythonLibrary.generate_soundbanks(soundbank_names, platforms, languages)
    except Exception: 
        logger.exception("Failed to generate soundbanks.")
        raise

def get_project_info()->dict: 
    try: 
        return WwisePythonLibrary.get_project_info()
    except Exception: 
        logger.exception("Failed to get project info for wwise project.")
        raise

def list_all_audio_files_at_path_on_file_explorer(root_path:str)->list[str]:
    if not root_path: 
        raise ValueError("Pass in a non empty root path in file explorer to retrieve audio files from.")
    
    try: 
        return WwisePythonLibrary.list_audio_files_at_path_file_explorer(root_path)
    except Exception: 
        logger.exception("Failed to retrieve audio at root path %r", root_path)
        raise

def set_object_reference( 
    object_path: str, 
    reference_type: str, 
    reference_path: str
) -> None:
    
    if not object_path or not reference_type: 
        raise ValueError("Ensure object path and reference name fields are not empty when setting object reference.")

    if reference_path is None:
        raise ValueError("Value cannot be None.")

    if isinstance(reference_path, str) and not reference_path:
        raise ValueError("String values cannot be empty.")

    try:
        WwisePythonLibrary.set_reference(object_path, reference_type, reference_path)
    except Exception: 
        logger.exception("Failed to set object reference.")
        raise

def set_object_property( 
    object_path: str, 
    property_name: str, 
    value: int|bool|str
) -> None:
    
    if not object_path or not property_name: 
        raise ValueError("Ensure object path and property name fields are not empty when setting object properties.")

    if value is None:
        raise ValueError("Value cannot be None.")

    if isinstance(value, str) and not value:
        raise ValueError("String values cannot be empty.")

    try:
        WwisePythonLibrary.set_property(object_path, property_name, value)
    except Exception: 
        logger.exception("Failed to set object property.")
        raise
    
def get_selected_objects() -> list[dict]:
    try: 
        selected_objects = WwisePythonLibrary.get_selected_objects()
        if not selected_objects:
            raise ValueError("No selection detected")
        return selected_objects
    except Exception: 
        logger.exception("Failed to retrieve selected objects in wwise.")
        raise

def unregister_game_object(name: str) -> None:
    if not name: 
        raise ValueError("Pass in a non empty name to indicate the game object that you want unregistered.")
    
    try: 
        WwisePythonLibrary.unregister_game_obj(name)
    except Exception: 
        logger.exception("Failed to unregister object %r", name)
        raise

def toggle_layout(requested_layout: str) -> None:
    if not requested_layout: 
        raise ValueError("Ensure requested layout is non empty.")

    try: 
        WwisePythonLibrary.toggle_layout(requested_layout)
    except Exception: 
        logger.exception("Failed to toggle to layout %r", requested_layout)
        raise

def get_all_property_name_valid_values() -> str:
    try:
        return WwisePythonLibrary.get_all_property_name_valid_values() 
    except Exception: 
        logger.exception("Failed to get all property names and associated valid value ranges.")
        raise

#==============================================================================
#                            Function Dictionary
#==============================================================================

@dataclass
class Command:
    func: callable
    doc: str

COMMANDS: dict[str, Command] = {
    "connect_to_wwise" : Command(
        func=connect_to_wwise,
        doc="Attempts to reconnect to the currently active wwise session."
            "Args: None"
    ),
    "resolve_all_path_relationships_in" : Command(
        func=resolve_all_path_relationships_in,
        doc="Returns a path-first index for the subtree rooted at `parent_path`."
            "Args: parent_path. Returns a list[dict]"
    ),
    "create_objects" : Command(
        func=create_child_objects,
        doc="Create child objects given names and types of objects and the parent path, if no parent path(s) specified, function will use prev_response_objects as parents."
            "Args: child_names : list[str], child_types: list[str], parent_paths : list[str] eg. ['\\Actor-Mixer Hierarchy\\Default Work Unit', ...], prev_response_objects='$last' if previous function needs to pass returned values into this function."
            "Object types : ActorMixer, Bus, AuxBus, RandomSequenceContainer, SwitchContainer, BlendContainer, Sound, WorkUnit, SoundBank, Folder, Attenuation."
    ), 
    "create_events" : Command(
        func=create_events,
        doc="Create multiple Wwise events in one batch."
            "Args: source_paths (list[str]), dst_parent_paths (list[str]), event_types (list[str]), event_names (list[str]). All four lists must have the same length. Returns: list[dict]"
    ),
    "create_game_objects" : Command(
        func=create_game_objects,
        doc="Create game objects in one batch."
            "Args : game_obj_names : list[str], positions : list[tuple[float,float,float]]. Returns None."
    ),
    "create_rtpcs": Command(
        func=create_rtpcs,
        doc="Creates rtpcs in one batch."
            "Args: rtpc_names : list[str], parent_paths : list[str], min_value : list[float], max_value : list[float]source_paths (list[str]), dst_parent_paths (list[str]), event_types (list[str]), event_names (list[str]). All four lists must have the same length. " \
            "Returns: list[dict]. parent path should always start with '\\Game Parameters'. If user does not specify min_values or max_values use 0.0 for min and 100.0 for max."
    ),
    "create_switch_groups" : Command(
        func=create_switch_groups,
        doc="Creates a list of switch gorups"
            "Args: names: list[str], parent_paths : list[str]:" 
            "Returns: list[dict]. A parent path should always start with either '\\Switches'."
            "Note that if you are creating a new SwitchGroup, the Group must always be created first before its Children."
    ),
    "create_switches" : Command(
        func=create_switches,
        doc="Creates a list of switches"
            "Args: names: list[str], parent_paths : list[str]." 
            "Returns: list[dict]. The parent path should always start with either '\\Switches' and represents the SwitchGroup the given switch belongs to."
            "Note that if you are creating a new StateGroup, the Group must always be created first before its Children."
    ),
    "create_state_groups" : Command(
        func=create_state_groups,
        doc="Creates a list of state groups"
            "Args: names: list[str], parent_paths : list[str]:" 
            "Returns: list[dict]. A parent path should always start with either '\\States'."
            "Note that if you are creating a new Stateroup, the Group must always be created first before its Children."
    ),
    "create_states" : Command(
        func=create_states,
        doc="Creates a list of states"
            "Args: names: list[str], parent_paths : list[str]:" 
            "Returns: list[dict]. A parent path should always start with either '\\States'and represents the StateGroup the given state belongs to."
            "Note that if you are creating a new StateGroup, the Group must always be created first before its Children."
    ),
    "move_object_by_path" : Command(
        func=move_object_by_path,
        doc="Moves the object from the source path to the new destination parent path. All child objects will be moved along with the parent."
            "Args: source_path : str, destination_parent_path : str, Returns a dict"
    ), 
    "rename_objects" : Command(
        func=rename_objects, 
        doc ="Renames a list of objects either by passing in a list of the objects' paths or by include prev_response_objects='$last' if a previous function need to pass returned values into this function."
             "Args: paths_of_objects_to_rename : list[str] | None, prev_response_objects: list[dict] | None, names: list[str]. Returns list[str]"
    ), 
    "import_audio_files" : Command(
        func=import_audio, 
        doc="Imports every audio file via its absolute path into the desired Wwise object path (include the object to be imported into the path as well). Validate destination path exists first via resolve_all_path_relationships_in if uncertain."
            "Args: source_paths: list[str], destination_paths: list[str]. Returns list[dict]"
    ),
    "list_all_event_names" : Command(
        func=list_all_event_names, 
        doc="List all events names"
              "Args: None, Returns list[str]"
    ),
    "list_all_rtpc_names" : Command(
        func=list_all_rtpc_names, 
        doc="List all rtpc names in wwise project"
            "Args: None, Returns list[str]"
    ),
    "list_all_switchgroups_and_switches" : Command(
        func=list_all_switchgroups_and_switches, 
        doc="List all switches grouped by their parent switch groups in a dict eg. [SwitchGroupName: [SwitchName, ...]]"
            "Args: None, Returns list[str]"
    ),
    "list_all_stategroups_and_states" : Command(
        func=list_all_stategroups_and_states, 
        doc="List all states grouped by their parent state groups in a dict eg. [StateGroupName: [StateName, ...]]"
            "Args: None, Returns dict[str, list[str]]"
    ),
    "list_all_game_objects_in_wwise" : Command(
        func=list_all_game_objects, 
        doc="List all game objects present in the wwise session."
            "Args: None, Returns list[dict]"
    ),
    "post_event" : Command(
        func=post_event, 
        doc="Posts the event by its name on the game object specified by its name after a delay in milliseconds"
            "If no game object is specified, the event will be posted on the 'Global' game object which should be used for 2D sounds like Ambiences."
            "If the specified game object does not exist, it will be created automatically at time of call."
            "If user does not specify delay_ms, assume post immediately so set delay_ms = 0."
            "Types of events : Play, Stop, Pause, Break, Seek"
            "Args: event_name: str, game_obj_name : str, delay_ms : int. Returns None"
    ),
    "set_rtpc" : Command(
        func=set_rtpc, 
        doc="Sets an RTPC on the specified game object using the given object name and RTPC parameter name. You can define start and end values over a duration (in milliseconds)." 
            "If no game object is specified, the RTPC is applied to the global game object 'Global'."
            "Args : game_object_name : str, rtpc_name : str, start : float, end : float, duration : int (milliseconds) , Returns None"
    ), 
    "set_state" : Command(
        func=set_state, 
        doc="Sets the state by the state group name it belongs to and the name of the state itself"
            "Args : state_group : str, state : str, delay_ms : int, Returns None"
    ), 
    "set_switch" : Command(
        func=set_switch, 
        doc="Sets the switch by the switch group name it belongs to and the name of the switch itself"
            "Args : game_obj_name : str, switch_group: str, switch : str, delay_ms : int, Returns None"
    ),
    "move_game_obj" : Command(
        func=move_game_obj, 
        doc="Moves the game object by its name from its start position to the desired end position over a duration (ms). A delay (ms) can be set to schedule the start of the movement ramp." 
            "If no game object with the specified name exist, one will be created."
            "Args : game_obj_name : str, start_pos : tuple(float, float, float), end_pos : tuple(float, float, float), duation_ms : int (ms), delay_ms : int(ms). Returns None"
    ),
    "stop_all_sounds" : Command(
        func=stop_all_sounds, 
        doc="Stops all sounds on all game objects created in the captured session"
            "Args: None. Returns None."
    ), 
    "include_in_soundbank" : Command(
        func=include_in_soundbank, 
        doc="Includes the specified objects (i.e events, work units or folders) in the specifed soundbank by path"
            "Args: include_paths : list[str], soundbank_paths : list[str]. Returns list[dict]"
    ), 
    "generate_soundbanks" : Command(
        func=generate_soundbanks, 
        doc="Generates the soundbanks given a list of soundbanks names, a list of platforms and a list of languages."
            "If unsure of what platforms to include, use 'Windows' or call the function : get_project_info."
            "If unsure on what languages to include, use 'English(US) or call the function : get_project_info." 
            "Args: soundbank_names : list[str], platforms : list[str], languages : list[str], Returns None"
    ), 
    "get_project_info" : Command(
        func=get_project_info, 
        doc="Returns the wwise project metadata, useful for determining languages and platforms avaialble in the project"
            "Args: None. Returns a dict"
    ),
    "get_all_audio_files_at_path_on_file_explorer" : Command(
        func=list_all_audio_files_at_path_on_file_explorer, 
        doc="Returns the path to all audio files given the parent folder path on file explorer (eg. 'C:/Audio')"
            "Args: root_path : str. Returns a list[str]"
    ),
    "set_object_reference" : Command(
        func=set_object_reference,
        doc="Sets a Wwise object's reference (e.g. Attenuation, OutputBus) to a target object."
            "Args: object_path : str, reference_type : str, reference_path : str. Returns dict."
    ),
    "set_object_property" : Command(
        func=set_object_property,
        doc="Sets the property of the object to a new value given its path in wwise"
            "Args: object_path : str, property_name : str, value: int | bool | str. Returns dict."
    ),
    "retrieve_selected_objs" : Command(
        func=get_selected_objects, 
        doc ="Retrives the currently selected object(s) in wwise."
             "Args: none. Returns a list[dicts]"
    ),
    "unregister_gameobject" : Command(
        func=unregister_game_object, 
        doc ="Unregisters the game object by specifying its name"
             "Args: name : str. Returns None."
    ),
    "toggle_layout" : Command(
        func=toggle_layout, 
        doc ="Toggles current layout in wwise to the requested layout. "
             "Valid layout types : Designer, Profiler, Soundbank, Mixer, Audio Object Profiler, Voice Profiler, Game Object Profiler"
             "Args: requested_layout : str. Returns none."
    ),
    "get_all_property_name_and_valid_value_types" : Command(
        func=get_all_property_name_valid_values, 
        doc ="Return a newline-formatted help string listing the correct WAAPI property identifiers for the specified Wwise object type."
             "Args: None. Returns: str."
    )
}

def list_commands()-> list[str]: 
    
    """
    Return each available command with its signature, e.g.
    'create_event(parent:str, name:str, type:str)'.
    """

    specs = []
    for name, cmd in COMMANDS.items():
        sig  = f"{name}{inspect.signature(cmd.func)}"
        hint = cmd.doc.strip() if cmd.doc else ""
        # put the hint on its own new line
        specs.append(f"{sig}\n    {hint}")
    return specs

#  A. parse a "verb(arg,…)" legacy string
def _parse_call(call_str: str) -> tuple[str, list, dict]:
    tree = ast.parse(call_str, mode="eval")
    if not isinstance(tree.body, ast.Call):
        raise ValueError(f"Expected func(...), got: {call_str}")

    verb   = tree.body.func.id
    args   = [ast.literal_eval(a) for a in tree.body.args]
    kwargs = {kw.arg: ast.literal_eval(kw.value)
              for kw in tree.body.keywords}
    return verb, args, kwargs

#  B. helper to extract .ids / .name from list-of-dicts 
def _extract_attr(obj, attr):
    if isinstance(obj, list):
        return [d[attr] for d in obj if isinstance(d, dict) and attr in d]
    if isinstance(obj, dict):
        return obj.get(attr)
    return getattr(obj, attr)

#  C. $var resolver (works on scalars / list / dict) 
def _resolve(val, store):
    if isinstance(val, str) and val.startswith("$"):
        key, *rest = val[1:].split(".", 1)
        if key not in store:
            raise KeyError(f"Variable '{key}' not found")
        obj = store[key]
        if rest:
            obj = _extract_attr(obj, rest[0])
        return obj
    if isinstance(val, list):
        return [_resolve(v, store) for v in val]
    if isinstance(val, dict):
        return {k: _resolve(v, store) for k, v in val.items()}
    return val

def _run_plan_sync(plan: list[any]) -> list[dict[str, any]]:
    store: dict[str, any] = {}        # per-plan variable bucket
    log  : list[dict[str, any]] = []

    for step in plan:
        #   Legacy string mode 
        if isinstance(step, str):
            verb, args, kwargs = _parse_call(step)
            args   = _resolve(args, store)      # allow $var inside lists
            kwargs = _resolve(kwargs, store)
            save_as = None                      # no explicit name in legacy
        #   Dict style  
        else:
            verb   = step["command"]
            args   = []                         # dict style uses keywords
            kwargs = _resolve(step["args"], store)
            save_as = step.get("save_as")

        #   Execute & validate 
        if verb not in COMMANDS:
            raise ValueError(f"Unknown command '{verb}'")
        func = COMMANDS[verb].func
        inspect.signature(func).bind_partial(*args, **kwargs)
        result = func(*args, **kwargs)

        #   Store results 
        store["last"] = result
        if save_as:
            store[save_as] = result

        log.append(
            {"command": verb, 
             "kwargs": kwargs,
             "result": result})

    return log

#==============================================================================
#                       MCP defintion & related functions
#==============================================================================

mcp = FastMCP(
    name = "Wwise-MCP Server",
    version = "1.0"
)

@mcp.tool()
async def list_wwise_commands()-> list[str]:
    
    """
    Return each available command with its signature,
    e.g. 'create_events(source_paths (list[str]), dst_parent_paths (list[str]), event_types (list[str]), event_names (list[str]))'.
    """

    return list_commands()

@mcp.tool()
async def execute_plan( plan: list[str]) -> dict [str, any]:

    """
    Execute a JSON list of call-strings produced by Claude.
    Returns simple success/failure info.
    """
    
    log = await anyio.to_thread.run_sync(_run_plan_sync, plan)

    return {"status": "ok", "steps_executed": len(log), "log": log}

# Run the server
if __name__ == "__main__":
    
    configure_logger()
    try: 
        logger.info("Starting Wwise-MCP server…")
        mcp.run(transport="stdio")
    except Exception: 
        logger.exception("Fatal server error")
        raise
    finally:
        WwisePythonLibrary.disconnect_from_wwise_client()