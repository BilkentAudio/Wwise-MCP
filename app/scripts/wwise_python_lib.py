from pathlib import Path
from typing import Iterable, Mapping, Any
import math 
import secrets
import time
import logging
import wwise_session as WwiseSession

from wwise_errors import (
    WwisePyLibError,
    WwiseValidationError,
    WwiseObjectNotFoundError,
    WwiseApiError
)

# Set up logger for this module
logger = logging.getLogger(__name__)

# ==============================================================================
#                      Waapi Client & Call Wrapper
# ==============================================================================

def connect_to_waapi(): 
    WwiseSession.connect_to_waapi()

def disconnect_from_wwise_client(): 
    WwiseSession.disconnect_from_wwise_client()

def waapi_call(
    uri: str, 
    args: Mapping[str, Any] | None = None, 
    options: Mapping[str, Any] | None = None, 
    **kw : Any
)-> Any:
    if not uri or not isinstance(uri, str): 
        raise ValueError("uri must be a non-empty string when calling waapi_call.")
    
    return WwiseSession.waapi_call(uri, args or {}, options=options, **kw)

# ==============================================================================
#                               Soundbank 
# ==============================================================================

def get_project_info() -> dict:
    """
    Retrieve information about the currently open Wwise project.
    
    Returns:
        dict: Project information including name, path, platform details, etc.
        
    Raises:
        WwiseApiError: If the WAAPI call fails or no project is open.
    """
    try:
        response = waapi_call("ak.wwise.core.getProjectInfo", {})
        
        if response is None:
            raise WwiseApiError(
                "WAAPI returned None when fetching project info (no project may be open)",
                operation="ak.wwise.core.getProjectInfo"
            )
        
        return response
    
    except WwisePyLibError:
        raise
    
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error fetching project info: {str(e)}",
            operation="ak.wwise.core.getProjectInfo",
            details={"error_type": type(e).__name__}
        )

def get_all_languages() -> list[str]:
    """
    Retrieve all languages configured in the current Wwise project.
    
    Returns:
        list[str]: List of language names (e.g., ['English(US)', 'French(France)']).
                   Returns empty list if no languages are configured.
        
    Raises:
        WwiseApiError: If project info cannot be retrieved.
        WwiseValidationError: If project info response is malformed.
    """
    try:
        response = get_project_info()
        
        if "languages" not in response:
            raise WwiseValidationError(
                "Project info response missing 'languages' field"
            )
        
        languages = [lang["name"] for lang in response["languages"]]
        return languages
    
    except WwisePyLibError:
        raise
    
    except KeyError as e:
        raise WwiseValidationError(
            f"Malformed language data in project info: missing {str(e)} field"
        )
    
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error fetching languages: {str(e)}",
            operation="ak.wwise.core.getProjectInfo",
            details={"error_type": type(e).__name__}
        )

def get_all_platforms() -> list[str]:
    """
    Retrieve all platforms configured in the current Wwise project.
    
    Returns:
        list[str]: List of platform names (e.g., ['Windows', 'PlayStation 5', 'Xbox Series X']).
        
    Raises:
        WwiseApiError: If project info cannot be retrieved.
        WwiseValidationError: If project info response is malformed or missing platforms.
    """
    try:
        response = get_project_info()
        
        if "platforms" not in response:
            raise WwiseValidationError(
                "Project info response missing 'platforms' field"
            )
        
        platforms = [platform["name"] for platform in response["platforms"]]
        
        if not platforms:
            raise WwiseValidationError(
                "No platforms configured in the project"
            )
        
        return platforms
    
    except WwisePyLibError:
        raise
    
    except KeyError as e:
        raise WwiseValidationError(
            f"Malformed platform data in project info: missing {str(e)} field"
        )
    
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error fetching platforms: {str(e)}",
            operation="ak.wwise.core.getProjectInfo",
            details={"error_type": type(e).__name__}
        )

def get_all_soundbanks() -> list[str]:
    """
    Retrieve all SoundBanks configured in the current Wwise project.
    
    Returns:
        list[str]: List of SoundBank names. Returns empty list if no SoundBanks exist.
        
    Raises:
        WwiseApiError: If the WAAPI call fails.
        WwiseValidationError: If the response is malformed.
    """
    args = {
        "from": {"path": ["\\SoundBanks"]},
        "transform": [{"select": ["descendants"]}],
        "options": {"return": ["name", "type", "path"]}
    }
    
    try:
        response = waapi_call("ak.wwise.core.object.get", args)
        
        if response is None:
            raise WwiseApiError(
                "WAAPI returned None when fetching SoundBanks",
                operation="ak.wwise.core.object.get",
                details={"path": "\\SoundBanks"}
            )
        
        if "return" not in response:
            raise WwiseValidationError(
                "Response missing 'return' field when fetching SoundBanks"
            )
        
        # Filter objects of type 'SoundBank'
        soundbanks = [
            obj["name"] for obj in response["return"] 
            if obj.get("type") == "SoundBank"
        ]
        
        return soundbanks
    
    except WwisePyLibError:
        raise
    
    except KeyError as e:
        raise WwiseValidationError(
            f"Malformed SoundBank data: missing {str(e)} field"
        )
    
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error fetching SoundBanks: {str(e)}",
            operation="ak.wwise.core.object.get",
            details={
                "error_type": type(e).__name__,
                "path": "\\SoundBanks"
            }
        )

def include_in_soundbank(
    include_paths: list[str], 
    soundbank_path: str
) -> list[dict]:
    """
    Add objects to a SoundBank's inclusions list.
    
    Note: This operation is NOT atomic. If a failure occurs, all previous
    inclusions will have succeeded. The returned list contains responses for
    successfully included objects before the failure.
    
    Args:
        include_paths: List of Wwise object paths to include in the SoundBank.
        soundbank_path: Path to the target SoundBank.
    
    Returns:
        list[dict]: List of WAAPI responses for each successful inclusion operation.
        
    Raises:
        WwiseValidationError: If inputs are invalid.
        WwiseApiError: If any inclusion operation fails.
    """
    if not include_paths:
        raise WwiseValidationError("include_paths list cannot be empty")
    
    if not soundbank_path or not soundbank_path.strip():
        raise WwiseValidationError("soundbank_path cannot be empty")
    
    result: list[dict] = []
    
    for i, include_path in enumerate(include_paths):
        if not include_path or not include_path.strip():
            raise WwiseValidationError(
                f"include_path at index {i} cannot be empty"
            )
        
        args = {
            "soundbank": soundbank_path,
            "operation": "add",
            "inclusions": [{
                "object": include_path,
                "filter": ["events", "structures"]
            }]
        }
        
        try:
            response = waapi_call("ak.wwise.core.soundbank.setInclusions", args)
            
            if response is None:
                raise WwiseApiError(
                    f"WAAPI returned None when including object at index {i}",
                    operation="ak.wwise.core.soundbank.setInclusions",
                    details={
                        "soundbank_path": soundbank_path,
                        "include_path": include_path,
                        "index": i
                    }
                )
            
            result.append(response)
        
        except WwisePyLibError:
            raise
        
        except Exception as e:
            raise WwiseApiError(
                f"Failed to include object at index {i}: {str(e)}",
                operation="ak.wwise.core.soundbank.setInclusions",
                details={
                    "error_type": type(e).__name__,
                    "soundbank_path": soundbank_path,
                    "include_path": include_path,
                    "index": i
                }
            )
    
    return result

def generate_soundbanks(
    soundbanks: list[str], 
    platforms: list[str], 
    languages: list[str] = None
) -> dict:
    """
    Generate SoundBanks for specified platforms and languages.
    
    Args:
        soundbanks: List of SoundBank names to generate.
        platforms: List of platform names to generate for.
        languages: Optional list of language names. If None, generates for all project languages.
    
    Returns:
        dict: Generation result containing success/failure info and generated file paths.
        
    Raises:
        WwiseValidationError: If inputs are invalid.
        WwiseApiError: If the SoundBank generation fails.
    """
    if not soundbanks:
        raise WwiseValidationError("soundbanks list cannot be empty")
    
    if not platforms:
        raise WwiseValidationError("platforms list cannot be empty")
    
    # Validate individual items
    for i, sb in enumerate(soundbanks):
        if not sb or not sb.strip():
            raise WwiseValidationError(f"SoundBank name at index {i} cannot be empty")
    
    for i, platform in enumerate(platforms):
        if not platform or not platform.strip():
            raise WwiseValidationError(f"Platform name at index {i} cannot be empty")
    
    if languages is not None:
        if not languages:
            raise WwiseValidationError("languages list cannot be empty (use None for all languages)")
        for i, lang in enumerate(languages):
            if not lang or not lang.strip():
                raise WwiseValidationError(f"Language name at index {i} cannot be empty")
    
    # Build the payload
    payload = {
        "soundbanks": [{"name": sb} for sb in soundbanks],
        "platforms": platforms,
        "writeToDisk": True
    }
    
    if languages is not None:
        payload["languages"] = languages
    
    try:
        response = waapi_call("ak.wwise.core.soundbank.generate", payload)
        
        if response is None:
            raise WwiseApiError(
                "WAAPI returned None when generating SoundBanks",
                operation="ak.wwise.core.soundbank.generate",
                details={
                    "soundbanks": soundbanks,
                    "platforms": platforms,
                    "languages": languages
                }
            )
        
        return response
    
    except WwisePyLibError:
        raise
    
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error generating SoundBanks: {str(e)}",
            operation="ak.wwise.core.soundbank.generate",
            details={
                "error_type": type(e).__name__,
                "soundbanks": soundbanks,
                "platforms": platforms,
                "languages": languages
            }
        )
    
# ==============================================================================
#                  Game Objects & Playback in Wwise
# ==============================================================================

LISTENER_ID = 1
DEFAULT_GAME_OBJ_NAME = "Global"

def get_all_game_objs_in_wwise_session() -> list[dict]:
    return waapi_call("ak.wwise.core.profiler.getGameObjects", {"time": "capture"})

def register_default_listener()-> None:
    waapi_call("ak.soundengine.registerGameObj", 
                {"gameObject": LISTENER_ID, 
                 "name": "listener"}) 
    waapi_call("ak.soundengine.setDefaultListeners", 
               {"listeners" : [LISTENER_ID]})
        
def alloc_game_object_id(name : str) -> int:
    
    game_objs = get_all_game_objs_in_wwise_session().get("return",[])
    existing = {int(go["id"]) for go in game_objs}
    max_tries = 64

    if LISTENER_ID not in existing:
        register_default_listener()

    for _ in range(max_tries):
        gid = secrets.randbits(31)           
        
        if gid not in existing:
            waapi_call(
                "ak.soundengine.registerGameObj", 
                {"gameObject": gid, 
                 "name": name}) 
            waapi_call(
                "ak.soundengine.setListeners",
                {
                    "emitter":   gid,          # game object that produces sound
                    "listeners": [LISTENER_ID]        # one or many listener IDs
                }) 
            time.sleep(0.02) # short delay so the next read from capture gets the updated game obj list 
            return gid
    raise RuntimeError("Could not allocate a unique game object ID")

def ensure_game_obj(name: str) -> int:

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Provide a non empty string name when creating a game obj.")

    game_objs = get_all_game_objs_in_wwise_session().get("return",[])    
    cleansed_name = name.strip().lower()

    for game_obj in game_objs : 
        game_obj_name = game_obj["name"]
        
        if not isinstance(game_obj_name, str) or not game_obj_name.strip(): 
            continue

        if (game_obj_name.lower() == cleansed_name):
            return game_obj["id"]

    return alloc_game_object_id(name)

def set_game_obj_position(
    game_obj_name : str, 
    x : float, 
    y : float, 
    z : float)->None: 

    gid = ensure_game_obj(game_obj_name)

    origin  = {"x": x,   "y": y,   "z": z}
    forward = {"x": 0.0, "y": 1.0, "z": 0.0}
    up      = {"x": 0.0, "y": 0.0, "z": 1.0}
    
    return waapi_call("ak.soundengine.setPosition", {
        "gameObject": gid,
        "position": {
            "position": origin,
            "orientationFront": forward,
            "orientationTop":   up,
        }
    })

Vec3 = tuple[float, float, float]

def _norm_vec(v: Vec3) -> Vec3:
    x,y,z = v
    n = math.sqrt(x*x + y*y + z*z) or 1.0
    return (x/n, y/n, z/n)

def _dot(a: Vec3, b: Vec3) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])

def _lerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    return (a[0] + (b[0]-a[0])*t,
            a[1] + (b[1]-a[1])*t,
            a[2] + (b[2]-a[2])*t)

def _orthonormalize(front: Vec3, top: Vec3) -> tuple[Vec3, Vec3]:
    f = _norm_vec(front)
    # Gram–Schmidt: make top orthogonal to front, then normalize
    t = _sub(top, (f[0]*_dot(top,f), f[1]*_dot(top,f), f[2]*_dot(top,f)))
    if t == (0.0,0.0,0.0):
        t = (0.0,1.0,0.0)
    return f, _norm_vec(t)

def _enqueue_position(gid: int, pos: Vec3, front: Vec3, top: Vec3, *, due_in_s: float):
    waapi_call("ak.soundengine.setPosition", {
        "gameObject": gid,
        "position": {
            "position": {"x": pos[0], "y": pos[1], "z": pos[2]},
            "orientationFront": {"x": front[0], "y": front[1], "z": front[2]},
            "orientationTop":   {"x": top[0],   "y": top[1],   "z": top[2]},
        }
    }, due_in = due_in_s, wait = False)

def start_position_ramp(
    *,
    obj: str,
    start_pos: Vec3,
    end_pos: Vec3,
    duration_ms: int,
    step_ms: int = 16,
    front: Vec3 = (0.0, 1.0, 0.0),  
    top:   Vec3 = (0.0, 0.0, 1.0),  
)-> None:
    """
    Schedules an interpolation of (x,y,z) from start_pos to end_pos over duration_ms.
    Uses the dispatcher-backed waapi_call(due_in=..., wait=False) for each step.
    Returns a tiny handle with no-op stop/join (for API parity).
    """

    gid = ensure_game_obj(obj)

    f, t = _orthonormalize(front, top)

    if duration_ms <=0 :
        _enqueue_position(gid, start_pos, f, t, due_in_s=0.0)
        _enqueue_position(gid, end_pos,   f, t, due_in_s=0.0)
        return
    
    dur_s  = duration_ms / 1000.0
    dt_s   = max(0.001, step_ms / 1000.0)
    steps  = max(1, math.ceil(dur_s / dt_s))

    # First sample at t=0, last at t=dur_s; linear easing
    for i in range(steps + 1):
        a   = i / steps
        pos = _lerp(start_pos, end_pos, a)
        _enqueue_position(gid, pos, f, t, due_in_s=a * dur_s)

def create_game_obj(game_obj_name : str, position : Vec3) -> None: 
    return set_game_obj_position(game_obj_name, position[0], position[1], position[2])

def unregister_game_obj(name: str) -> None:
    id : int = ensure_game_obj(name)
    waapi_call("ak.soundengine.unregisterGameObj", {"gameObject": id})

def stop_all_sounds():
    game_objs = get_all_game_objs_in_wwise_session().get("return",[])
    
    for game_obj in game_objs:
        gid = game_obj["id"]
        waapi_call("ak.soundengine.stopAll", {"gameObject": gid})
 
# ==============================================================================
#             Creating, Listing & Posting Events in Wwise
# ==============================================================================

EVENT_TYPES = {
    "play"  : 1, 
    "stop"  : 2,
    "pause" : 7,
    "resume": 9,
    "break" : 34,
    "seek"  : 36
}

EVENT_TYPE_NAMES = list(EVENT_TYPES.keys()) 

OBJECTS_ALLOWEDEVENTS = {
    "ActorMixer"             :  EVENT_TYPE_NAMES[1:],
    "Bus"                    :  EVENT_TYPE_NAMES[1:],
    "AuxBus"                 :  [EVENT_TYPE_NAMES[5]],
    "RandomSequenceContainer":  EVENT_TYPE_NAMES,
    "SwitchContainer"        :  EVENT_TYPE_NAMES,
    "BlendContainer"         :  EVENT_TYPE_NAMES,
    "Sound"                  :  EVENT_TYPE_NAMES,
    "WorkUnit"               :  None, 
    "SoundBank"              :  None, 
    "Folder"                 :  None
}
   
def create_event(
    source_path : str, 
    dst_parent_path : str, 
    event_type : str, 
    event_name : str
) -> dict:
    """
    Create a Wwise event with associated action.
    
    Args:
        source_path: Path to the source object for the action target
        dst_parent_path: Path to the parent where event will be created
        event_type: Type of action (must be key in ACTION_TYPES)
        event_name: Name for the new event
    
    Returns:
        dict: Contains 'event' and 'action' response objects
    
    Raises:
        WwiseValidationError: If input validation fails
        WwiseObjectNotFoundError: If paths cannot be resolved
        WwiseApiError: If WAAPI calls fail
    """
    
    # 1. Validate inputs
    if not all([source_path, dst_parent_path, event_name, event_type]):
        raise WwiseValidationError("All parameters must be non-empty. "
        f"Received: source_path={bool(source_path)}, "
        f"dst_parent_path={bool(dst_parent_path)}, "
        f"event_name={bool(event_name)}, "
        f"event_type={bool(event_type)}"
    )

    event_type = event_type.lower()

    if event_type not in EVENT_TYPES:
        raise WwiseValidationError(
        f"Invalid event_type '{event_type}'. "
        f"Valid types: {', '.join(sorted(set(EVENT_TYPES.keys())))}")
    
    try:
        # 2. Resolve parent object
        parent_ref = get_object_at_path(dst_parent_path)
        if not parent_ref: 
            raise WwiseObjectNotFoundError(f"Failed to create event: {event_name}. The parent path supplied is invalid. Please specify a valid parent path for the new event.")
        if "id" not in parent_ref or not parent_ref["id"]:
            raise WwiseApiError(f"Failed to create event: {event_name}. Parent destination object does not contain an id attribute or has no id. Please specify a valid parent path object.") 
        parent_id = parent_ref["id"]

        # 3. Resolve source object
        source_object = get_object_at_path(source_path)
        if not source_object:
            raise WwiseObjectNotFoundError(f"Failed to create event: {event_name}. Source Object does not exist. The provided source path is invalid.")
        if "id" not in source_object or not source_object["id"]:
            raise WwiseApiError(f"Source Object does not contain an id attribute or has no id. Please specify a valid source object.")
        source_object_id = source_object["id"]

        # 4. Create event
        event_response = waapi_call(
            "ak.wwise.core.object.create", {
            "parent": parent_id,
            "type": "Event",
            "name": event_name, 
            "onNameConflict": "rename"
        })

        if not event_response or "id" not in event_response or not event_response["id"]:
            raise WwiseApiError(
                f"Event creation for '{event_name}' returned invalid response",
                operation="create_event",
                details={"response": event_response}
            )
        logger.info(f"Created event with ID: {event_response['id']}")

        # 5. Create action
        action_response = waapi_call(
            "ak.wwise.core.object.create", {
            "parent": event_response["id"],
            "type": "Action",
            "name": event_name,
            "@ActionType": EVENT_TYPES[event_type],
            "@Target": source_object_id
        })

        if not action_response or "id" not in action_response:
            raise WwiseApiError(
                f"Action creation for event '{event_name}' returned invalid response",
                operation="create_action",
                details={"response": action_response}
            )
        logger.info(f"Created action with ID: {action_response['id']}")

        return {
            "event": event_response,
            "action": action_response
        }
    except (WwiseValidationError, WwiseObjectNotFoundError):
        # These are expected errors - re-raise as-is
        raise
    
    except WwiseApiError as e:
        # API errors - re-raise as-is
        raise
    
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error creating event '{event_name}': {e}", exc_info=True)
        raise WwiseApiError(
            f"Unexpected error creating event '{event_name}': {str(e)}",
            operation="create_event"
        ) from e

def list_all_event_names(
    filter_spec: str | None = None
) -> list[str]:
    """
    Return the names of all matching objects in the \\Events tree.

    Parameters
    ----------
    filter_spec  : str | None
        • None or ''            → all Events in the project
        • absolute path         → e.g. r"\\Events\\Ambience" (all descendants)
        • name fragment         → fuzzy-matches names anywhere in \\Events

    Returns
    -------
    list[str] - the object *names* (not paths).  May be empty.

    Raises
    ------
    RuntimeError on WAAPI failure.
    """
    spec = (filter_spec or "").strip()

    # 1️. decide the subtree we start from + optional name filter
    if spec.startswith("\\"):                 # absolute path
        start_path = spec.rstrip("\\")
        name_cond  = ""                       # no extra name filter
    elif spec:                                # just a name fragment
        start_path = r"\Events"
        name_cond  = spec
    else:                                     # empty -> all Events
        start_path = r"\Events"
        name_cond  = ""

    # 2️. build WAAPI query
    transform = [{"select": ["descendants"]}]
    if name_cond:
        transform.append({"where": ["name:matches", name_cond]})    
    transform.append({"where": ["type:isIn", ["Event"]]})

    query_args = {"from": {"path": [start_path]}, "transform": transform}
    query_opts = {"return": ["name"]}

    res = waapi_call("ak.wwise.core.object.get", query_args, options=query_opts)
    if not res or "return" not in res:
        raise RuntimeError("WAAPI call failed or returned no data")

    return [obj["name"] for obj in res["return"]]

def post_event(
  event_name: str,
  game_obj: str,
  delay_ms: int
) -> None:

  if delay_ms < 0:
    raise ValueError("delay_ms must be >= 0")
  
  if not game_obj: 
    game_obj = DEFAULT_GAME_OBJ_NAME

  ensure_game_obj(game_obj)
  
  if delay_ms < 0:
    raise ValueError("delay_ms must be >= 0")
  if not game_obj:
    raise ValueError("game object name must not be null")

  gid = ensure_game_obj(game_obj)  # your existing registrar / resolver

  waapi_call(
    "ak.soundengine.postEvent",
    {"event": event_name, "gameObject": gid},
    due_in=delay_ms / 1000.0,   # schedule via dispatcher
    wait=False                  # fire-and-forget
    )

def stop_event(
    event_name: str,
    *, 
    obj: str = "Global",
    fade_ms: int = 100) -> None:

    """
    Stops all voices started by `event_name` on `obj`.
    Uses Wwise's ExecuteActionOnEvent WAAPI call.
    """
    gid = ensure_game_obj(obj)

    waapi_call("ak.soundengine.executeActionOnEvent", {     
        "event": event_name,
        "actionType": 0,            # 'pause', 'resume', 'stop'…
        "gameObject": gid,
        "transitionDuration": fade_ms,
        "fadeCurve": 0
    })

# ==============================================================================
#              Creating Game Syncs (States, Switches, Rtpcs) in Wwise
# ==============================================================================

def create_rtpc(
    name: str,
    parent: str = "\\Game Parameters\\Default Work Unit",
    vmin: float = 0.0,
    vmax: float = 100.0,
    default: float | None = None,
    on_conflict: str = "rename") -> dict:
    
    """
    Make a Game Parameter (RTPC) under the Game Parameters hierarchy.

    Returns the WAAPI object dict (id, name, path, etc.).
    """
    # 1) Create the Game Parameter object
    created = waapi_call("ak.wwise.core.object.create", {
        "parent": parent,             
        "type": "GameParameter",
        "name": name,
        "onNameConflict": on_conflict 
    })
    obj = created.get("return", created)  
    gid = obj["id"]

    # 2) Set its numeric range
    payload = {
    "object": gid,         # GUID string or full object path
    "min": float(vmin),
    "max": float(vmax),
    "onCurveUpdate": "stretch"   # or "stretch" / "crop"
    }

    waapi_call("ak.wwise.core.gameParameter.setRange",payload)

    # 3) Set a default value
    if default is not None:
        waapi_call("ak.wwise.core.object.setProperty", {
            "object": gid,
            "property": "InitialValue",  
            "value": float(default)
        })

    return obj

def create_switch_or_state_types(
    name: str, 
    parent_path: str, 
    type : str, # Switch, SwitchGroup, State, StateGroup
    on_conflict: str = "rename") -> dict:
    
    return waapi_call("ak.wwise.core.object.create", {
        "parent": parent_path,
        "type": type,
        "name": name,
        "onNameConflict": on_conflict
    })

# ==============================================================================
#         Game Syncs (States, Switches, Rtpcs) Setters in Wwise
# ==============================================================================

def set_state( 
    state_group: str, 
    state_name: str, 
    delay_ms: int
) -> None:
    
    """
    Sets `state_name` in the specified 'state group' in the wwise project
    """

    waapi_call("ak.soundengine.setState", {
        "stateGroup": state_group,   
        "state": state_name,
        }, 
        due_in=delay_ms/1000.0,
        wait=False
    )

def set_switch( 
    switch_group: str, 
    switch_name: str,
    delay_ms: int, 
    *,
    obj: str = "Global"
) -> None:
    
    """
    Sets `switch_name` in the specified 'switch_group'
    """

    gid = ensure_game_obj(obj) 

    waapi_call("ak.soundengine.setSwitch", {
        "switchGroup": switch_group,   
        "switchState": switch_name,
        "gameObject" : gid
        }, 
        due_in=delay_ms/1000.0,
        wait=False
    )

def set_rtpc( 
    rtpc_name: str,
    value: float,
    *,
    obj: str = "Global"
) -> None:
    
    """
    Sets `rtpc_name` on `obj`.
    • duration_ms > 0  -> smooth ramp
    • obj="Global"     -> global scope (id 0)
    """
    
    gid = ensure_game_obj(obj)            

    waapi_call("ak.soundengine.setRTPCValue", {
        "rtpc":              rtpc_name,  
        "value":             value,
        "gameObject":        gid
    })

def ramp_rtpc(
    rtpc, 
    start, 
    end, 
    duration_ms,
    *, 
    obj="Global", 
    step_ms=50):
    
    """
    Schedules an RTPC ramp via the dispatcher over a defined duration in milliseconds.
    """

    if duration_ms < 0:
        raise ValueError("duration_ms must be >= 0")

    gid = ensure_game_obj(obj)

    # Edge case: zero duration -> just set final value immediately
    if duration_ms == 0:
        waapi_call("ak.soundengine.setRTPCValue",
                   {"rtpc": rtpc, "value": end, "gameObject": gid},
                   wait=False)
        return

    dur_s  = duration_ms / 1000.0
    dt_s   = max(0.001, step_ms / 1000.0)
    steps  = max(1, math.ceil(dur_s / dt_s))

    # Linear ramp
    for i in range(steps + 1):
        t = i / steps
        value = start + (end - start) * t
        waapi_call("ak.soundengine.setRTPCValue",
                   {"rtpc": rtpc, "value": value, "gameObject": gid},
                   due_in=t * dur_s,   # schedule relative to now
                   wait=False)         # fire-and-forget

# ==============================================================================
#          Game Syncs (States, Switches, Rtpcs) Getters
# ==============================================================================

GAME_PARAM_ROOT  = r"\Game Parameters"
RTPC_TYPE       = ["GameParameter"]

SWITCH_ROOT = r"\Switches"
SWITCH_GROUP_TYPES = ["SwitchGroup"]
SWITCH_TYPE = ["Switch"]

STATE_ROOT  = r"\States"
STATE_GROUP_TYPES = ["StateGroup"]
STATE_TYPE  = ["State"]

def list_gamesync_names(root : str, type : list[str], filter_spec: str | None = None) -> list[str]:
    """
    Return the *names* of all Game Sync objects in the \\Game Syncs tree.

    Parameters
    ----------
    client       : WaapiClient
    root         : str
    type         : list[str]
    filter_spec  : str | None
        • None / ""               → every RTPC in the project
        • absolute path           → e.g. r"\\Game Parameters\\Vehicle" (descendants only)
        • name fragment           → fuzzy-matches names anywhere in \\Game Parameters
    

    Returns
    -------
    list[str]   – Game Sync object names (may be empty).

    Raises
    ------
    RuntimeError  – if the WAAPI query fails.
    """
    spec = (filter_spec or "").strip()

    # Decide the subtree and optional name filter
    if spec.startswith("\\"):                 # absolute path
        start_path = spec.rstrip("\\")
        name_cond  = ""
    elif spec:                                # just a name fragment
        start_path = root
        name_cond  = spec
    else:                                     # no filter → entire tree
        start_path = root
        name_cond  = ""

    transform = [{"select": ["descendants"]}]
    if name_cond:
        transform.append({"where": ["name:matches", name_cond]})
    transform.append({"where": ["type:isIn", type]})

    query_args = {"from": {"path": [start_path]}, "transform": transform, "options": {"return": ["name"]}}

    res = waapi_call("ak.wwise.core.object.get", query_args)
    if not res or "return" not in res:
        raise RuntimeError("WAAPI call failed or returned no data")

    return [obj["name"] for obj in res["return"]]

def list_all_rtpc_names(filter_spec: str | None = None) -> list[str]:
    return list_gamesync_names(GAME_PARAM_ROOT, RTPC_TYPE, filter_spec)

def get_all_gamesync_types(
    root_path: str,
    gamesync_child_types: list[str],
    filter_spec: str | None = None,
    *,
    include_path: bool = False
) -> list[dict]:
    """
    Returns a list like:
        [{"id": "<GUID>", "name": "<ChildName>"}]            (default)
        or [{"id": ..., "name": ..., "path": "..."}] if include_path=True
    """
    spec = (filter_spec or "").strip()

    # Build transform
    transform: list[dict] = [
        {"select": ["descendants"]},
        {"where": ["type:isIn", gamesync_child_types]},
    ]
    if spec:
        # substring match; switch to name:matches if you want regex
        transform.insert(1, {"where": ["name:contains", spec]})

    args = {
        "from": {"path": [root_path]},
        "transform": transform,
    }
    ret_fields = ["id", "name"] + (["path"] if include_path else [])
    opts = {"return": ret_fields}

    res = waapi_call("ak.wwise.core.object.get", args, options=opts)

    items = (res or {}).get("return")
    if not items:
        # Make the failure explicit so callers can handle it
        raise RuntimeError("WAAPI ak.wwise.core.object.get returned no 'return' field")

    # Filter out any partial objects defensively
    out = []
    for o in items:
        _id = o.get("id")
        _name = o.get("name")
        if not (_id and _name):
            continue
        if include_path:
            _path = o.get("path")
            if not _path:
                continue
            out.append({"id": _id, "name": _name, "path": _path})
        else:
            out.append({"id": _id, "name": _name})
    return out

def get_parent_map_for_gamesync_child_ids(gamesync_child_ids: Iterable[str]) -> dict[str, tuple[str, str] | None]:
    """
    For each child_id, returns (parent_id, parent_name).
    If a parent can't be resolved, value is None for that key.
    Tries a fast batch call first; falls back to per-ID select if needed.
    """
    gamesync_child_ids = [sid for sid in gamesync_child_ids if sid]  # normalize
    if not gamesync_child_ids:
        return {}

    parent_map: dict[str, tuple[str, str] | None] = {}
    
    # per-ID, select the parent then read its fields ----------
    for sid in gamesync_child_ids:
        try:
            args = {
                "from": {"id": [sid]},
                "transform": [
                    {"select": ["parent"]}  # move selection to the parent object
                ],
            }
            # ask for id + name (type/path optional if your build returns them)
            opts = {"return": ["id", "name"]}
            res = waapi_call("ak.wwise.core.object.get", args, opts)
            items = (res or {}).get("return", [])

            if items:
                parent_id = items[0].get("id")
                parent_nm = items[0].get("name")
                if parent_id and parent_nm:
                    parent_map[sid] = (parent_id, parent_nm)
                    continue

            parent_map[sid] = None  # couldn't resolve
        except Exception:
            parent_map[sid] = None

    return parent_map

def build_state_groups_from_list(gamesync_children : list[dict], parent_map : dict[str, tuple[str, str] | None])-> dict[str, str] : 
    groups: dict[str, list[str]] = {}
    
    for s in gamesync_children:
        sid, sname = s["id"], s["name"]
        parent = parent_map.get(sid)
        if parent is None:
            continue
        _, gname = parent
        groups.setdefault(gname, []).append(sname)

    result = [[gname, *sorted(snames, key=str.casefold)]
            for gname, snames in groups.items()]
    result.sort(key=lambda row: row[0].casefold())

    return result 

def get_all_gamesyncgroups_and_gamesyncs_grouped(root_path : str, gamesync_child_types : list[str]) -> dict[str, list[str]]:
    """
    Returns {StateGroupName: [StateName, ...]}.
    """
    gamesyncs = get_all_gamesync_types(root_path, gamesync_child_types)
    parent_map = get_parent_map_for_gamesync_child_ids([s["id"] for s in gamesyncs])
    groups: dict[str, list[str]] = {}

    for s in gamesyncs:
        parent = parent_map.get(s["id"])
        if not parent:
            continue
        _, gname = parent
        groups.setdefault(gname, []).append(s["name"])

    for g in groups:
        groups[g].sort(key=str.casefold)
    return groups

def get_all_stategroups_and_states_grouped(): 
   return get_all_gamesyncgroups_and_gamesyncs_grouped(STATE_ROOT, STATE_TYPE)

def get_all_switchgroups_and_switches_grouped(): 
   return get_all_gamesyncgroups_and_gamesyncs_grouped(SWITCH_ROOT, SWITCH_TYPE)

# ==============================================================================
#                      Wwise Object Getters
# ==============================================================================

def get_selected_objects() -> list[dict]:
    """
    Fetch currently selected objects in Wwise.
    
    Returns:
        list[dict]: List of selected object dictionaries. Empty list if nothing selected.
        
    Raises:
        WwiseApiError: If the WAAPI call fails.
    """
    operation = "ak.wwise.ui.getSelectedObjects"
    
    try:
        response = waapi_call(operation, {})
        
        if not isinstance(response, dict):
            raise WwiseApiError(
                f"WAAPI returned unexpected type: {type(response).__name__}",
                operation=operation,
                details={"response_type": type(response).__name__}
            )

        objs = response.get("objects", [])
        
        if not isinstance(objs, list):
            raise WwiseApiError(
                f"'objects' field is not a list: {type(objs).__name__}",
                operation=operation,
                details={"objects_type": type(objs).__name__}
            )
        
        return objs
    
    except (WwisePyLibError):
        raise
    
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error: {str(e)}",
            operation=operation,
            details={
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        ) from e

def get_fields_from_objects(
    object_ids: list[str], 
    fields: list[str]
) -> list[dict]:
    """
    Retrieve specified fields from Wwise objects given their IDs.
    
    Args:
        object_ids: List of Wwise object GUIDs.
        fields: List of field names to retrieve (e.g., ['name', 'type', 'path']).
        'children' field is automatically filtered out.
    
    Returns:
        list[dict]: List of objects with requested fields.
        
    Raises:
        WwiseValidationError: If object_ids or fields are empty.
        WwiseApiError: If the WAAPI call fails.
    """
    if not object_ids:
        raise WwiseValidationError("object_ids list cannot be empty")
    
    if not fields:
        raise WwiseValidationError("fields list cannot be empty")
    
    # Filter out 'children' field as it's not supported in this context
    clean_fields = [f for f in fields if f.lower() != "children"]
    
    if not clean_fields:
        raise WwiseValidationError(
            "No valid fields remaining after filtering (only 'children' was provided)"
        )
    
    args = {
        "from": {"id": object_ids},
        "options": {"return": clean_fields}
    }
    
    try:
        response = waapi_call("ak.wwise.core.object.get", args)
        
        if response is None:
            raise WwiseApiError(
                "WAAPI returned None when fetching object fields",
                operation="ak.wwise.core.object.get",
                details={"object_ids": object_ids, "fields": clean_fields}
            )
        
        return response.get("return", [])
    
    except WwisePyLibError:
        raise
    
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error fetching object fields: {str(e)}",
            operation="ak.wwise.core.object.get",
            details={
                "error_type": type(e).__name__,
                "object_ids": object_ids,
                "fields": clean_fields
            }
        )

def get_object_at_path(path: str) -> dict:
    """
    Retrieve a Wwise object by its full path.
    
    Args:
        path: Full Wwise object path (e.g., '\\Actor-Mixer Hierarchy\\Default Work Unit\\MySound').
    
    Returns:
        dict: Object info containing 'id', 'name', 'type', and 'path' fields.
        
    Raises:
        WwiseValidationError: If path is empty or invalid.
        WwiseObjectNotFoundError: If no object exists at the specified path.
        WwiseApiError: If the WAAPI call fails.
    """
    if not path or not path.strip():
        raise WwiseValidationError("Object path cannot be empty")
    
    args = {
        "from": {"path": [path]},
        "options": {"return": ["id", "name", "type", "path"]}
    }
    
    try:
        response = waapi_call("ak.wwise.core.object.get", args)
        
        if response is None:
            raise WwiseApiError(
                "WAAPI returned None when retrieving object by path",
                operation="ak.wwise.core.object.get",
                details={"path": path}
            )
        
        objects = response.get("return", [])
        
        if not objects:
            raise WwiseObjectNotFoundError(
                f"No object found at path: {path}",
                path=path
            )
        
        return objects[0]
    
    except WwisePyLibError:
        raise
    
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error retrieving object at path: {str(e)}",
            operation="ak.wwise.core.object.get",
            details={
                "error_type": type(e).__name__,
                "path": path
            }
        )

# ==============================================================================
#                   Editing Objects in Wwise 
# ==============================================================================

def rename_objects(
    objects: list[dict], 
    names: list[str]
) -> list[str]:
    """
    Rename multiple Wwise objects.
    
    Note: This operation is NOT atomic. If a failure occurs, all previous
    renames will have succeeded. The returned list contains IDs of 
    successfully renamed objects before the failure.

    Args:
        objects: List of Wwise object dicts (must contain 'id' field).
        names: List of new names corresponding to each object.
    
    Returns:
        list[str]: List of object IDs that were successfully renamed.
        
    Raises:
        WwiseValidationError: If inputs are invalid or mismatched lengths.
        WwiseApiError: If any rename operation fails.
    """
    if not objects:
        raise WwiseValidationError("objects list cannot be empty")
    
    if not names:
        raise WwiseValidationError("names list cannot be empty")
    
    if len(objects) != len(names):
        raise WwiseValidationError(
            f"Mismatch between objects ({len(objects)}) and names ({len(names)}) count"
        )
    
    # Validate all objects have 'id' field before attempting any operations
    for i, obj in enumerate(objects):
        if not isinstance(obj, dict) or "id" not in obj:
            raise WwiseValidationError(
                f"Object at index {i} is missing 'id' field"
            )
    
    result: list[str] = []
    
    for i, (obj, new_name) in enumerate(zip(objects, names)):
        try:
            response = waapi_call(
                "ak.wwise.core.object.setName",
                {"object": obj["id"], "value": new_name}
            )
            
            # Assuming the response contains the object ID on success
            result.append(obj["id"])
        
        except WwisePyLibError:
            raise
        
        except Exception as e:
            raise WwiseApiError(
                f"Failed to rename object at index {i}: {str(e)}",
                operation="ak.wwise.core.object.setName",
                details={
                    "error_type": type(e).__name__,
                    "object_id": obj["id"],
                    "new_name": new_name,
                    "index": i
                }
            )
    
    return result

def set_property(
    object_path: str,
    property_name: str,
    value: int | bool | str) -> None:
    """
    Sets the property of the object given object's path and .

    Parameters
    ----------
    object_path : str
        path to the object in Wwise
    property_name : str
        The WAAPI / WAQL property name – e.g. 'IsStreamingEnabled',
        'IsLoopingEnabled', 'UseGameAuxSends', ...
    value : int, bool, bool
        What to set the property to.
    """
    if not object_path: 
        raise ValueError("You must specify the object paths to randomize")

    return waapi_call(
        "ak.wwise.core.object.setProperty",
        {"object": object_path, 
            "property": property_name, 
            "value": value})

def move_object_by_path(source_path: str, dst_path: str):
    """
    Move an object (by its path) to a new parent (by path).
    If use_ids=True, it resolves to GUIDs via your view["meta"] for robustness.
    Returns the WAAPI move result dict (id,name,path).
    """

    src_obj = get_object_at_path(source_path)
    if not src_obj: 
        raise ValueError(f"Source path not found: {source_path}")
    src_id = src_obj["id"]

    dst_obj = get_object_at_path(dst_path)
    if not dst_obj: 
        raise ValueError(f"Destination path not found: {dst_path}")
    dst_id = dst_obj["id"]

    res = waapi_call("ak.wwise.core.object.move", args={"object": src_id, "parent": dst_id})

    if not isinstance(res, dict):
        raise RuntimeError(f"Move failed: {res}")

    # res only contains id and name. 
    moved_id = res["id"]   
    moved = waapi_call(
    "ak.wwise.core.object.get",
    args={"from": {"id": [moved_id]}},                     
    options={"options": {"return": ["id", "name", "path"]}},
    )

    return moved

# ==============================================================================
#           Resolving Path Structures in Wwise
# ==============================================================================

def fetch_nodes(parent_path : str) -> str:
    return_fields = ["id","name","path"]
    
    # 1) Grab the parent root (this returns exactly one object)
    args1 = {"from": { "path": [parent_path]}}
    opts1 = {"return": return_fields }
    root_res = waapi_call("ak.wwise.core.object.get", args1, opts1)

    root_list = root_res.get("return", [])
    root = root_list[0] if root_list else None

    # 2) Get all descendants (single selector only)
    args2 = {"from": { "path": [parent_path] }, "transform": [{"select": ["descendants"]}]}
    opts2 = {"return": return_fields}
    desc_res = waapi_call("ak.wwise.core.object.get", args2, opts2)
    descendants = desc_res.get("return", [])

    # 3) Combine (root + descendants)
    return ([root] if root else []) + descendants

# ==============================================================================
#              Importing Audio Files into Wwise
# ==============================================================================

AUDIO_EXTS = {".wav", ".aiff", ".aif", ".ogg"} 

def import_audio(
    source: str,
    destination: str,
    *,
    language: str = "SFX",
    originals_sub: str = "SFX",
    recurse: bool = True
) -> list[dict]:
    
    """
    Import every audio file under *source* (a folder) into Wwise under the given parent path.
    • Assumes source is absolute objectPath strings eg. "C:\\Users\\SomeName\\Downloads\\SoundSFX"
    • Builds absolute object path strings in wwise eg." \\Actor-Mixer Hierarchy\\...\\SoundName"
    • Returns the WAAPI objects list
    """

    # --- normalise inputs ---------------------------------------------
    source = Path(source).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    # ensure parent path has ONE leading backslash, no trailing
    destination = "\\" + destination.strip("\\")

    # --- build import table -------------------------------------------
    imports = []
    iterator = source.rglob("*") if recurse else source.iterdir()

    for file in iterator:
        if file.suffix.lower() not in AUDIO_EXTS:
            continue

        # relative folders → keep hierarchy
        rel_parts = file.relative_to(source).with_suffix("").parts
        obj_name  = rel_parts[-1]
        container_path = "\\".join(rel_parts[:-1])           # may be ''
        pieces = [destination.strip("\\")]
        if container_path:
            pieces.append(container_path)
        pieces.append(obj_name)

        object_path = "\\" + "\\".join(pieces)               # absolute path

        imports.append({
            "audioFile": str(file),
            "objectPath": object_path
        })

    if not imports:
        raise ValueError("No audio files found under that folder")

    # --- call WAAPI ----------------------------------------------------
    args = {
        "importOperation": "useExisting",          # or "createNew", "replaceExisting"
        "default": {
            "importLanguage": language,
            "objectType": "Sound",
            "originalsSubFolder": originals_sub,
        },
        "imports": imports,
    }

    res = waapi_call(
        "ak.wwise.core.audio.import",
        args,
        options={"return": ["id", "name", "path"]},
    )

    return res["objects"]   

def list_audio_files_at_path_file_explorer(
    root_path : str,
    *, 
    recurse: bool = True,
    include_hidden: bool = False
) -> list[str]:
    
    """Return audio files under *root* that would be considered by import_audio()."""

    root_path = Path(root_path).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(root_path)

    it: Iterable[Path] = root_path.rglob("*") if recurse else root_path.iterdir()

    def is_hidden(p: Path) -> bool:
        # cross-platform-ish hidden check (dotfiles). Windows attributes need extra work if you care.
        return any(part.startswith(".") for part in p.parts)

    files: list[str] = []

    for p in it:
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            if include_hidden or not is_hidden(p):
                files.append(p)
    return files

# ==============================================================================
#                   Creating Objects in Wwise
# ==============================================================================

def create_object(
    parent_id: str,
    child_name: str,
    child_type: str, 
    on_conflict: str = "rename"
) -> dict:
   
    """
    Creates the specified object type under `parent_path`.

    Returns the GUID (string) of the newly-created object.
    """
    try:  
        res: dict = []
        res = waapi_call(
                "ak.wwise.core.object.create",
                {
                 "parent": parent_id,          # WAQL or back-slash path
                 "type":   child_type,           # always "WorkUnit" for both cases
                 "name":   child_name,           # requested name for new work or folder 
                 "onNameConflict": on_conflict   # "fail", "rename", "replace", "merge") 
                }
        )
        return res   
    
    except Exception as e:
        raise RuntimeError(f"WAAPI error: {e}")

# ==============================================================================
#           Property Names & Valid Ranges for different Wwise Objects
# ==============================================================================

RANDOM_CONTAINER_PROPERTY_HELP = """
Random Container (WAAPI property names)

Play Type — RandomOrSequence  (0=Sequence, 1=Random)
Random Type — NormalOrShuffle  (0=Shuffle, 1=Standard)
Play Mode — PlayMechanismStepOrContinuous  (0=Continuous, 1=Step)
Loop — PlayMechanismLoop  (bool)
Infinite Looping — PlayMechanismInfiniteOrNumberOfLoops  (0=No. of Loops, 1=Infinite)
No. of Loops — PlayMechanismLoopCount  (int)
Always Reset Playlist — PlayMechanismResetPlaylistEachPlay  (bool)
Transitions (Enable) — PlayMechanismSpecialTransitions  (bool)
Transition Type — PlayMechanismSpecialTransitionsType  (0=Xfade (amp), 4=Xfade (power), 1=Delay, 2=Sample accurate, 3=Trigger rate)
Transition Duration — PlayMechanismSpecialTransitionsValue  (seconds)
At End of Playlist — RestartBeginningOrBackward  (0=Play in reverse order, 1=Restart)
Limit Repetition — RandomAvoidRepeating  (bool)
Limit Repetition To — RandomAvoidRepeatingCount  (int)

"""

CORE_MIXING_PROPERTY_HELP = """
Core Mixing (on container)

Volume — Volume  (dB)
Pitch — Pitch  (cents)
Low-pass — Lowpass  (0-100)
High-pass — Highpass  (0-100)

"""

def get_all_property_name_valid_values() -> str: 
    return RANDOM_CONTAINER_PROPERTY_HELP + CORE_MIXING_PROPERTY_HELP

# ==============================================================================
#                   Editor Layouts in Wwise
# ==============================================================================

LAYOUTS = ["Designer", "Profiler", "Soundbank", "Mixer", "Audio Object Profiler", "Voice Profiler", "Game Object Profiler"]

def toggle_layout(request_layout : str)->dict:
    
    if request_layout not in LAYOUTS:
        logger.exception("No such layout exists : %r", request_layout)
        
        raise ValueError("toggle_layout can only one of accept these args : " \
        "Designer, Profiler, Soundbank, Mixer, Audio Object Profiler, Voice Profiler, Game Object Profiler. " \
        "They are case sensitive.")
    
    return waapi_call("ak.wwise.ui.layout.switchLayout", {"name": request_layout})