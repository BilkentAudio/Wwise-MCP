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
#                          Shared validation helpers
# ==============================================================================

def _require_non_none(response, operation, **details):
    """WAAPI failures raise (the client runs with allow_exception=True), so a
    None response is an anomaly. Surface it as an error instead of returning a
    fake-empty success. Mirrors the inline None->raise guard in get_project_info."""
    if response is None:
        raise WwiseApiError(
            f"WAAPI returned None for {operation}",
            operation=operation,
            details=details or None,
        )
    return response


def _validate_timeout_seconds(timeout: float, field_name: str = "timeout") -> float:
    """Reject zero, negative, non-finite, or non-numeric timeout values.
    WAAPI calls with timeout <= 0 fail immediately; non-finite (inf, nan) causes
    undefined wait behavior in the dispatcher."""
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise WwiseValidationError(
            f"{field_name} must be a number (seconds), got {type(timeout).__name__}"
        )
    timeout_f = float(timeout)
    if not math.isfinite(timeout_f) or timeout_f <= 0:
        raise WwiseValidationError(
            f"{field_name} must be a finite number > 0, got {timeout!r}"
        )
    return timeout_f


# object.set listMode values shared by the playlist / effect-list wrappers.
_OBJECT_SET_LIST_MODES = frozenset({"replaceAll", "append"})


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

        return _require_non_none(
            response,
            "ak.wwise.core.getProjectInfo",
            hint="no project may be open",
        )

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

_SETINCLUSIONS_FILTER_VALUES = frozenset({"events", "structures", "media"})


def include_in_soundbank(
    include_paths: list[str],
    soundbank_path: str,
    filter: list[str] | None = None,
) -> list[dict]:
    """
    Add objects to a SoundBank's inclusions list.

    Note: This operation is NOT atomic. If a failure occurs, all previous
    inclusions will have succeeded. The returned list contains responses for
    successfully included objects before the failure.

    Args:
        include_paths: List of Wwise object paths to include in the SoundBank.
        soundbank_path: Path to the target SoundBank.
        filter: Optional inclusion-type filter passed to the WAAPI
            setInclusions call. Allowed values are "events", "structures",
            and "media"; at most 3 entries, each unique. When omitted,
            defaults to ["events", "structures"] (the previous fixed
            behaviour).

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

    if filter is None:
        effective_filter = ["events", "structures"]
    else:
        if not isinstance(filter, list):
            raise WwiseValidationError(
                f"filter must be a list when provided, got {type(filter).__name__}"
            )
        non_str = [f for f in filter if not isinstance(f, str)]
        if non_str:
            raise WwiseValidationError(f"filter entries must be strings, got non-str: {non_str!r}")
        bad = [f for f in filter if f not in _SETINCLUSIONS_FILTER_VALUES]
        if bad:
            raise WwiseValidationError(
                f"filter values not in {{events, structures, media}}: {bad}"
            )
        if len(filter) > 3:
            raise WwiseValidationError(
                f"filter accepts at most 3 entries (WAAPI maxItems:3), got {len(filter)}"
            )
        seen: set[str] = set()
        duplicates = [f for f in filter if f in seen or seen.add(f)]
        if duplicates:
            raise WwiseValidationError(
                f"filter values must be unique, duplicates: {sorted(set(duplicates))}"
            )
        effective_filter = list(filter)

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
                "filter": effective_filter
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
    step_ms: int = 100,
    delay_ms: int,
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
    
    if delay_ms < 0:
        delay_ms = 0
    
    dur_s  = duration_ms / 1000.0
    delay_s = delay_ms / 1000.0
    dt_s   = max(0.001, step_ms / 1000.0)
    steps  = max(1, math.ceil(dur_s / dt_s))

    # First sample at t=0, last at t=dur_s; linear easing
    for i in range(steps + 1):
        a   = i / steps
        pos = _lerp(start_pos, end_pos, a)
        _enqueue_position(gid, pos, f, t, due_in_s=a * dur_s + delay_s)

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
  delay_ms: int,
  wait: bool = False,
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

  delay_s = delay_ms / 1000.0
  call_kwargs: dict[str, Any] = {
    "due_in": delay_s,
    "wait": wait,
  }
  # Default reply timeout (WwiseSession._DEFAULT_TIMEOUT = 1.0s) is shorter than
  # any non-trivial delay, so wait=True + delay_ms>0 would otherwise time out
  # before the scheduled dispatch fires. Extend timeout to cover the schedule.
  if wait and delay_s > 0:
    call_kwargs["timeout"] = WwiseSession._DEFAULT_TIMEOUT + delay_s

  waapi_call(
    "ak.soundengine.postEvent",
    {"event": event_name, "gameObject": gid},
    **call_kwargs,
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
    if items is None:
        raise RuntimeError("WAAPI ak.wwise.core.object.get returned no 'return' field")
    if not items:
        return []

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
#                        Wwise Queries
# ==============================================================================

_DEFAULT_RETURN_FIELDS = ["id", "name", "type", "path"]
 
def run_waql(waql: str, return_fields: list[str] | None = None) -> list[dict]:
    """Execute a raw WAQL query against the project.
 
    Thin passthrough over ak.wwise.core.object.get using the `waql` argument.
    Use for any ad-hoc query — referencesTo, descendants, where-filters,
    ofType scans, etc.
 
    Args:
        waql: A WAQL query string, e.g.
              '$ "\\Game Parameters\\Default Work Unit\\BlendTest" select referencesTo'.
        return_fields: WAAPI return fields. Defaults to ['id','name','type','path'].
 
    Returns:
        list[dict] of matching objects.
    """
    operation = "ak.wwise.core.object.get"
 
    if not waql or not waql.strip():
        raise WwiseApiError(
            "waql must be a non-empty WAQL query string.",
            operation=operation,
            details={"waql": waql}
        )
 
    # Match get_objects_info: `options` is nested inside the args dict, and waapi_call
    # is called with a single args argument. Passing options as a third positional is
    # silently dropped by waapi_call, which is why return fields never threaded before.
    args = {
        "waql": waql,
        "options": {"return": return_fields or _DEFAULT_RETURN_FIELDS},
    }
 
    try:
        response = waapi_call(operation, args)
 
        if not isinstance(response, dict):
            raise WwiseApiError(
                f"WAAPI returned unexpected type: {type(response).__name__}",
                operation=operation,
                details={"response_type": type(response).__name__}
            )
 
        objs = response.get("return", [])
 
        if not isinstance(objs, list):
            raise WwiseApiError(
                f"'return' field is not a list: {type(objs).__name__}",
                operation=operation,
                details={"return_type": type(objs).__name__}
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
                "error_message": str(e),
                "waql": waql
            }
        ) from e
 
 
def find_references_to(object_ref: str, return_fields: list[str] | None = None) -> list[dict]:
    """Find every object that references the given object (inverse-reference lookup).
 
    One-shot answer to "what currently uses this object?". Works for any
    referenceable target: Game Parameters (RTPC control inputs, Blend Track
    LayerCrossFadeControlInput, attenuation-curve inputs), Buses, Switches/States,
    Effects, Attenuations, etc.
 
    Args:
        object_ref: A GUID '{XXXXXXXX-...}', a project path
                    '\\Game Parameters\\Default Work Unit\\BlendTest', or a
                    qualified name 'GameParameter:BlendTest'.
        return_fields: WAAPI return fields. Defaults to ['id','name','type','path'].
 
    Returns:
        list[dict] of objects that reference object_ref.
    """
    operation = "ak.wwise.core.object.get"
 
    if not object_ref or not object_ref.strip():
        raise WwiseApiError(
            "object_ref must be a non-empty GUID, path, or qualified name.",
            operation=operation,
            details={"object_ref": object_ref}
        )
 
    ref = object_ref.strip()
 
    # referencesTo returns the immediate referrers. Two shapes come back:
    #   1. A NAMED object that holds the reference directly on itself, e.g. a Switch
    #      Container's @SwitchGroupOrStateGroup. These are already the answer.
    #   2. An anonymous binding / list-element node, e.g. an RTPC/curve binding or a
    #      Music Switch Container assignment entry. These have no useful name and must
    #      be climbed via `owner` to reach the object that holds them.
    #
    # So we must NOT blindly climb: a fixed `select owner` over-climbs the case-1
    # objects (a tree object has a `parent`, not an `owner`, so `owner` returns empty
    # and the named result vanishes). Instead, keep named referrers as-is, and climb
    # `owner` only while the current node is unnamed. Depth varies by reference type
    # (RTPC = 1 hop, music assignment entries = 2), so climb until named rather than a
    # fixed number of hops, then dedupe.
    #
    # Note: tree-walks (`ancestors`/`parent`) don't help the anonymous nodes because
    # list-element binding nodes aren't in the object tree; `owner` is the link.
    # Paths/GUIDs/qualified-names all sit fine inside WAQL double quotes; a single
    # backslash in a path is literal in WAQL, so no runtime escaping is needed.
    _MAX_OWNER_HOPS = 8
 
    referrers = run_waql(f'$ "{ref}" select referencesTo', return_fields)
 
    resolved: list[dict] = []
    seen: set[str] = set()
    for obj in referrers:
        cur = obj
        hops = 0
        # Climb only while unnamed (i.e. still an anonymous binding/entry node) and we
        # still have an id to climb from. Named referrers skip this entirely.
        while cur and not cur.get("name") and cur.get("id") and hops < _MAX_OWNER_HOPS:
            owners = run_waql(f'$ "{cur["id"]}" select owner', return_fields)
            if not owners:
                break
            cur = owners[0]
            hops += 1
 
        if not cur:
            continue
        oid = cur.get("id")
        if oid is not None and oid in seen:
            continue
        if oid is not None:
            seen.add(oid)
        resolved.append(cur)
 
    return resolved

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

def get_objects_info(object_paths: list[str], return_fields: list[str]) -> dict:
    """
    Gets detailed information about a Wwise object by path, GUID, or qualified name.

    Args:
        object_ref: Wwise object path, GUID, or qualified name.
        return_fields: WAAPI return fields.

    Returns:
        dict containing the WAAPI response.
    """

    args = {
        "from": {
            "path": object_paths
        },
        "options": {
            "return": return_fields
        }
    }

    return waapi_call("ak.wwise.core.object.get", args)

def get_object_property_and_reference_names(object_path: str) -> dict:
    """
    Gets all valid WAAPI property and reference names for a Wwise object.

    This is useful for determining which '@Property' and '@@Property'
    fields may be queried or set on the specified object.

    Args:
        object_path: Wwise object path.
                     Example:
                     '\\Actor-Mixer Hierarchy\\Default Work Unit\\MyBlendContainer'

    Returns:
        dict containing valid properties and references for the object.
    """

    args = {
        "object": object_path
    }

    return waapi_call(
        "ak.wwise.core.object.getPropertyAndReferenceNames",
        args
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

def set_object(
    object_path: str,
    properties: dict
) -> None:

    """
    Sets one or more properties/references on an existing Wwise object using

    ak.wwise.core.object.set with onNameConflict='merge'.

    Use this for list-type or complex fields that cannot be set via
    setProperty or setReference, such as:
    - @Arguments     : state/switch group subscription on MusicSwitchContainer.
                        Must be a list of MusicArgumentsSlot dicts:
                        [{'type': 'MusicArgumentsSlot', 'name': '', '@Argument': '<StateGroup or SwitchGroup path>'}]
    - @Entries       : child-to-state/switch assignments on MusicSwitchContainer.
                        Must be a list of MultiSwitchEntry dicts:
                        [{'type': 'MultiSwitchEntry', 'name': '', '@EntryPath': [{'type': 'EntryPathSlot', 'name': '', '@EntryPathObject': '<State or Switch path>'}], '@AudioNode': '<child path>'}]
    - @PlaylistRoot / @TransitionRoot : nested music structures using MusicPlaylistItem dicts.

    Parameters
    ----------
    object_path : str
        Path to the target Wwise object (must already exist).
    properties : dict
        '@PropertyName': value pairs. Values can be scalars, lists, or
        nested dicts as required by the WAAPI schema for that field.

    Example
    -------

    object_set(
        r"\Containers\Music\MusicSwitchContainer\CombatEnd",
        {"@Arguments": [{"type": "MusicArgumentsSlot", "name": "", "@Argument": r"\States\Default Work Unit\CombatEndState"}]}
    )
    """

    if not object_path:
        raise ValueError("object_path must be specified")

    if not properties:
        raise ValueError("properties must not be empty")

    return waapi_call(
        "ak.wwise.core.object.set",
        {"objects": [
            {
                "object": object_path,
                "onNameConflict": "merge",
                **properties
            }]
        }
    )

def assign_music_arguments(
    container_path: str,
    group_paths: list[str]
) -> None:

    """
    Assigns one or more State/Switch Groups as Arguments to a MusicSwitchContainer.
    This sets the Switch/State tab "Group" field — the source the container reads
    from to decide which child to play.

    Parameters
    ----------

    container_path : str
        Path to an existing MusicSwitchContainer.

    group_paths : list[str]
        One or more StateGroup or SwitchGroup paths, e.g.
        r"\States\Default Work Unit\MusicState".

    Example
    -------

    assign_music_arguments(
        r"\Containers\Music\MusicSwitchContainer",
        [r"\States\Default Work Unit\MusicState"]
    )
    """

    if not container_path:
        raise ValueError("container_path must be specified")

    if not group_paths:
        raise ValueError("group_paths must contain at least one path")

    arguments = [
        {"type": "MusicArgumentsSlot", "name": "", "@Argument": path}
        for path in group_paths
    ]

    return set_object(container_path, {"@Arguments": arguments})

def assign_music_entries(
    container_path: str,
    entries: list[dict]
) -> None:

    """
    Assigns child-to-state/switch mappings on a MusicSwitchContainer's Assigned
    Objects view. Each entry maps a State or Switch (or a tuple across multiple
    Arguments) to a child audio node (MusicPlaylistContainer, MusicSegment, or
    nested MusicSwitchContainer).

    Parameters
    ----------

    container_path : str
        Path to an existing MusicSwitchContainer. Its @Arguments must already
        be assigned via assign_music_arguments first.

    entries : list[dict]
        Each dict has:
          - 'state_or_switch' : str | list[str]
              Single path for single-argument containers, or a list of paths
              in the same order as the container's @Arguments for multi-arg.
          - 'audio_node' : str
              Path to the child audio node to play when the state/switch matches.

    Example
    -------

    assign_music_entries(
        r"\Containers\Music\MusicSwitchContainer",

        [
            {"state_or_switch": r"\States\Default Work Unit\MusicState\Explore",
             "audio_node": r"\Containers\Music\MusicSwitchContainer\Explore"},
            {"state_or_switch": r"\States\Default Work Unit\MusicState\Combat",
             "audio_node": r"\Containers\Music\MusicSwitchContainer\Combat"},
        ]
    )
    """

    if not container_path:
        raise ValueError("container_path must be specified")

    if not entries:
        raise ValueError("entries must contain at least one entry")

    multi_switch_entries = []

    for entry in entries:
        sos = entry.get("state_or_switch")
        audio_node = entry.get("audio_node")

        if not sos or not audio_node:
            raise ValueError(
                "Each entry must have 'state_or_switch' and 'audio_node' keys."
            )

        paths = [sos] if isinstance(sos, str) else list(sos)

        entry_path = [
            {"type": "EntryPathSlot", "name": "", "@EntryPathObject": p}
            for p in paths
        ]

        multi_switch_entries.append({
            "type": "MultiSwitchEntry",
            "name": "",
            "@EntryPath": entry_path,
            "@AudioNode": audio_node,
        })

    return set_object(container_path, {"@Entries": multi_switch_entries})

def set_playlist_root(
    playlist_container_path: str,
    items: list[dict],
    loop_count: int = 0

) -> None:

    """
    Sets the @PlaylistRoot of a MusicPlaylistContainer — i.e. populates its
    playlist tree with MusicPlaylistItems. Replaces any existing playlist.
    Parameters
    ----------

    playlist_container_path : str
        Path to an existing MusicPlaylistContainer.
    items : list[dict]
        Each item dict has:
          - 'segment' : str       (path to a MusicSegment)
          - 'playlist_item_type' : int, optional
                1 = Segment (default), 0 = Group
          - 'loop_count' : int, optional (default 1)
          - 'children' : list[dict], optional (for nested group items)

    loop_count : int
        Loop count on the root playlist node (0 = infinite).
    Example
    -------

    set_playlist_root(
        r"\Containers\Music\MusicSwitchContainer\CombatEnd\Victory",
        items=[
            {"segment": r"\Containers\Music\...\VictorySegment", "playlist_item_type": 1}
        ]
    )
    """

    if not playlist_container_path:
        raise ValueError("playlist_container_path must be specified")

    if not items:
        raise ValueError("items must contain at least one playlist item")

    def build_item(item):
        d = {
            "type": "MusicPlaylistItem",
            "name": "",
            "@PlaylistItemType": item.get("playlist_item_type", 1),
            "@LoopCount": item.get("loop_count", 1),
        }


        if "segment" in item:
            d["@Segment"] = item["segment"]


        if "children" in item:
            d["children"] = [build_item(c) for c in item["children"]]
        return d

    root = {
        "type": "MusicPlaylistItem",
        "name": "",
        "@LoopCount": loop_count,
        "children": [build_item(i) for i in items],
    }

    return set_object(playlist_container_path, {"@PlaylistRoot": root})

def _normalize_curve_point(point) -> dict:
    """Normalize a curve point into the WAAPI {'x', 'y', 'shape'} dict form."""
    if isinstance(point, dict):
        if "x" not in point or "y" not in point:
            raise ValueError(f"curve point dict must contain 'x' and 'y': {point}")
        return {"x": point["x"], "y": point["y"], "shape": point.get("shape", "Linear")}
    if isinstance(point, (tuple, list)):
        if len(point) == 2:
            x, y, shape = (*point, "Linear")
        elif len(point) == 3:
            x, y, shape = point
        else:
            raise ValueError(f"curve point tuple must be (x, y) or (x, y, shape): {point}")
        return {"x": x, "y": y, "shape": shape}
    raise TypeError(f"unsupported curve point type: {type(point).__name__}")

def add_rtpc_binding(
    object_path: str,
    control_input: str,
    property_name: str,
    points: list | None = None,
    notes: str = ""
) -> None:

    """
    Adds an RTPC binding (with optional curve) to an existing object's "@RTPC"
    list via set_object.

    This creates the RTPC *binding* — the link between a control input, a target
    property, and a curve. It does NOT create the control input: the game
    parameter / Modulator / MIDI object referenced by `control_input` must
    already exist, since it is passed by reference (path or GUID).

    Parameters
    ----------
    object_path : str
        Path to the target object that will host the RTPC (must already exist).
    control_input : str
        Path or GUID of an existing GameParameter, Modulator, or MIDI object.
        This is the x-axis source of the RTPC.
    property_name : str
        The property driven by the RTPC, e.g. "OutputBusVolume", "Volume",
        "Pitch", "Lowpass". Passed as the bare property name (no leading '@').
    points : list, optional
        Curve points. Each item may be either a dict
        ({"x": <float>, "y": <float>, "shape": <str>}) or a tuple
        ((x, y) or (x, y, shape)). 'shape' defaults to "Linear" when omitted.
        If None, @Curve is omitted and Wwise generates its default curve.
    notes : str, optional
        Notes string stored on the RTPC binding.

    Example
    -------

    add_rtpc(
        r"\Actor-Mixer Hierarchy\Default Work Unit\Engine",
        control_input=r"\Game Parameters\Default Work Unit\RPM",
        property_name="OutputBusVolume",
        points=[(0, -20.83), (1000, 21.85)]
    )
    """

    if not object_path:
        raise ValueError("object_path must be specified")

    if not control_input:
        raise ValueError("control_input must be specified")

    if not property_name:
        raise ValueError("property_name must be specified")

    rtpc = {
        "type": "RTPC",
        "name": "",
        "notes": notes,
        "@PropertyName": property_name,
        "@ControlInput": control_input,
    }

    if points is not None:
        if not points:
            raise ValueError("points must contain at least one point when provided")
        rtpc["@Curve"] = {
            "type": "Curve",
            "points": [_normalize_curve_point(p) for p in points],
        }

    return set_object(object_path, {"@RTPC": [rtpc]})

def set_reference(
    object_path: str,
    reference_name: str,
    value: str
) -> None:
    """
    Sets the reference of the object given object's path and value.

    Parameters
    ----------
    object_path : str
        path to the object in Wwise
    reference_name : str
        The WAAPI / WAQL reference name - e.g. 'Attenuation'
    value : str
       The path to the reference to.
    """
    if not object_path: 
        raise ValueError("You must specify the object paths to set reference for")

    return waapi_call(
        "ak.wwise.core.object.setReference",
        {"object": object_path, 
            "reference": reference_name, 
            "value": value},
        options={"return": ["id", "name", "path", "type"]},
    )

def set_property(
    object_path: str,
    property_name: str,
    value: int | bool | str
) -> None:
    """
    Sets the property of the object given object's path.

    Parameters
    ----------
    object_path : str
        path to the object in Wwise
    property_name : str
        The WAAPI / WAQL property name - e.g. 'IsStreamingEnabled',
        'IsLoopingEnabled', 'UseGameAuxSends', ...
    value : int, bool, str
        What to set the property to.
    """
    if not object_path: 
        raise ValueError("You must specify the object paths to randomize")

    return waapi_call(
        "ak.wwise.core.object.setProperty",
        {"object": object_path, 
            "property": property_name, 
            "value": value})

def set_randomizer(
    object_path: str, 
    property_name: str, 
    enabled: bool, 
    min_value: float, 
    max_value: float
) -> None:
    """
    Sets the randomizer for a given property on a Wwise object.
    Example property_name: "Volume", "Pitch", "Lowpass"
    """

    waapi_call("ak.wwise.core.object.setRandomizer", {
        "object": object_path,
        "property": property_name,
        "enabled": enabled,
        "min": min_value,
        "max": max_value
    })

def set_attenuation_curve(
    object_path: str,
    curve_type: str,
    use: str,
    points: list[dict] | None,
    platform: str = "Windows"
) -> None:
    """
    Sets an attenuation curve on a Wwise Attenuation object.

    Args:
        object_path: The ID (GUID), name, or path of the attenuation object.
                     Accepts project path, qualified name (Attenuation:Name), or GUID.

        curve_type: The type of attenuation curve. One of:
                    "VolumeDryUsage" | "VolumeWetGameUsage" | "VolumeWetUserUsage" |
                    "LowPassFilterUsage" | "HighPassFilterUsage" | "HighShelfUsage" |
                    "SpreadUsage" | "FocusUsage" |
                    "ObstructionVolumeUsage" | "ObstructionLPFUsage" | "ObstructionHPFUsage" | "ObstructionHSFUsage" |
                    "OcclusionVolumeUsage"   | "OcclusionLPFUsage"   | "OcclusionHPFUsage"   | "OcclusionHSFUsage"  |
                    "DiffractionVolumeUsage" | "DiffractionLPFUsage" | "DiffractionHPFUsage" | "DiffractionHSFUsage"|
                    "TransmissionVolumeUsage"| "TransmissionLPFUsage"| "TransmissionHPFUsage"| "TransmissionHSFUsage"

        use: "None"         - Curve disabled, no points.
             "Custom"       - Curve uses its own points (points arg required).
             "UseVolumeDry" - Curve mirrors the VolumeDryUsage curve.
             "UseProject"   - Curve uses the global curve from Project Settings.

        points: list of {"x": float, "y": float, "shape": str} — required when use="Custom".
                First point x MUST be 0.0, last point x MUST equal the attenuation's RadiusMax.
                RadiusMax MUST be set on the object before calling this function.
                shape: "Constant" | "Linear" |
                       "Log3" | "Log2" | "Log1" |
                       "InvertedSCurve" | "SCurve" |
                       "Exp1" | "Exp2" | "Exp3"

        platform: Unique name or GUID of the target platform. Defaults to "Windows".
                  Pass the null GUID "{00000000-0000-0000-0000-000000000000}" for an unlinked curve.
                  Do NOT pass "{CurrentPlatform}" — it is not a valid WAAPI value.
    """

    args = {
        "object": object_path,
        "platform": platform,
        "curveType": curve_type,
        "use": use,
        "points": points or []
    }

    waapi_call("ak.wwise.core.object.setAttenuationCurve", args)
        
def assign_child_to_switch(
    child_container_path: str,
    switch_path: str
) -> None:
    """
    Assigns a child object (e.g., Random Container) to a specific Switch within a Switch Container.
    Example: assign a "Grass" random container to the "Surface/Grass" switch.
    """

    waapi_call("ak.wwise.core.switchContainer.addAssignment", {
        "child": child_container_path,
        "stateOrSwitch": switch_path
    })

def assign_child_to_blend_track(
    blend_track_id: str,
    child_path: str,
    edges: list[dict] | None = None
) -> dict:

    if not blend_track_id:
        raise ValueError("blend_track_id must be a valid Wwise object GUID.")

    args = {
        "object": blend_track_id,
        "child": child_path
    }

    if edges is not None:
        args["edges"] = edges

    return waapi_call("ak.wwise.core.blendContainer.addAssignment", args)

def assign_child_to_random_sequence_playlist(
    container_path: str,
    child_paths: list[str],
    list_mode: str = "replaceAll",
) -> dict:

    if not container_path:
        raise ValueError("container_path must be a valid Wwise object path or GUID.")

    if not child_paths:
        raise ValueError("child_paths must be a non-empty list of Wwise object paths or GUIDs.")

    if list_mode not in _OBJECT_SET_LIST_MODES:
        raise WwiseValidationError(
            f"list_mode must be one of {sorted(_OBJECT_SET_LIST_MODES)}, got {list_mode!r}"
        )

    args = {
        "objects": [
            {
                "object": container_path,
                "@Playlist": [
                    {
                        "type": "PlaylistSlot",
                        "name": "",
                        "@PlaylistObject": child_path
                    }
                    for child_path in child_paths
                ]
            }
        ],
        "onNameConflict": "merge",
        "listMode": list_mode,
    }

    return waapi_call("ak.wwise.core.object.set", args)

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

def copy_object(source_path: str, dst_parent_path: str, on_name_conflict: str = "rename"):
    """
    Copy an object (by path) to a new parent (by path).
    on_name_conflict: "rename" | "replace" | "fail"
    Returns the WAAPI result dict (id, name, path) of the new copy.
    """

    src_obj = get_object_at_path(source_path)
    if not src_obj:
        raise ValueError(f"Source path not found: {source_path}")
    src_id = src_obj["id"]

    dst_obj = get_object_at_path(dst_parent_path)
    if not dst_obj:
        raise ValueError(f"Destination path not found: {dst_parent_path}")
    dst_id = dst_obj["id"]

    res = waapi_call("ak.wwise.core.object.copy", args={
        "object": src_id,
        "parent": dst_id,
        "onNameConflict": on_name_conflict,
    })

    if not isinstance(res, dict):
        raise RuntimeError(f"Copy failed: {res}")

    copied_id = res["id"]
    copied = waapi_call(
        "ak.wwise.core.object.get",
        args={"from": {"id": [copied_id]}},
        options={"options": {"return": ["id", "name", "path"]}},
    )

    return copied

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
#                     Music related 
# ==============================================================================

def get_music_transitions(
    music_object_path: str
) -> dict:
    """
    Retrieves authored MusicTransition objects from a music object's TransitionRoot.
    """
    root_result = waapi_call("ak.wwise.core.object.get", {
        "from": {
            "path": [music_object_path]
        },
        "options": {
            "return": [
                "id",
                "name",
                "type",
                "path",
                "@@TransitionRoot"
            ]
        }
    })

    root_objects = root_result.get("return", [])
    if not root_objects:
        return {"return": [], "note": "Object not found at path."}

    root_obj = root_objects[0]
    transition_root = root_obj.get("@@TransitionRoot")

    if not transition_root:
        return {"return": [], "note": "No TransitionRoot found.", "debug_root_obj": root_obj}

    transition_root_id = transition_root.get("id")
    if not transition_root_id:
        return {"return": [], "note": "TransitionRoot found but no ID.", "debug_transition_root": transition_root}

    return waapi_call("ak.wwise.core.object.get", {
        "from": {
            "id": [transition_root_id]
        },
        "transform": [
            {"select": ["descendants"]},
            {"where": ["type:isIn", ["MusicTransition"]]}
        ],
        "options": {
            "return": [
                "id", "name", "type", "path", "parent", "owner",
                "@SourceContextType", "@SourceContextObject",
                "@DestinationContextType", "@DestinationContextObject",
                "@ExitSourceAt",
                "@DestinationJumpPositionPreset",
                "@DestinationPlaylistJumpTo",
                "@UseTransitionObject",
                "@EnableSourceFadeOut",
                "@EnableDestinationFadeIn",
                "@EnableTransitionFadeIn",
                "@EnableTransitionFadeOut",
                "@FadeInDuration", "@FadeOutDuration",
                "@FadeInCurve", "@FadeOutCurve",
                "@PlayDestinationPreEntry",
                "@PlaySourcePostExit",
                "@PlayTransitionPreEntry",
                "@PlayTransitionPostExit",
                "@ExitSourceCustomCueMatchName",
                "@JumpToCustomCueMatchMode",
                "@JumpToCustomCueMatchName"
            ]
        }
    })

# ==============================================================================
#              Importing Audio Files into Wwise
# ==============================================================================

AUDIO_EXTS = {".wav", ".aiff", ".aif", ".ogg"} 

def import_audio_files(
    source_files: list[str],
    destination_paths: list[str],
    *,
    language: str = "SFX",
    originals_sub: str = "SFX",
    import_operation: str = "useExisting",  # "createNew" / "replaceExisting" also valid
) -> list[dict]:
    """
    Import specific audio files into Wwise using WAAPI.

    :param source_files: List of file system paths to audio files.
    :param destination_paths: List of Wwise object paths (same length as source_files).
                              e.g. "\\Actor-Mixer Hierarchy\\Default Work Unit\\SFX\\Gun\\Shot_01"
    :param language: Wwise importLanguage (default "SFX").
    :param originals_sub: Originals subfolder (e.g. "SFX").
    :param import_operation: "useExisting", "createNew", or "replaceExisting".
    :return: List of WAAPI objects returned by the import.
    """

    if len(source_files) != len(destination_paths):
        raise ValueError("source_files and destination_paths must have the same length")

    imports: list[dict] = []

    for src, dest in zip(source_files, destination_paths):
        # --- normalize & validate source file path ---
        src_path = Path(src).expanduser().resolve()
        if not src_path.exists():
            raise FileNotFoundError(f"Source file does not exist: {src_path}")

        if src_path.suffix.lower() not in AUDIO_EXTS:
            raise ValueError(f"Not a supported audio file: {src_path}")

        # --- normalize destination Wwise object path ---
        # ensure exactly one leading backslash, no trailing backslash
        object_path = "\\" + dest.strip("\\")

        imports.append(
            {
                "audioFile": str(src_path),
                "objectPath": object_path,
            }
        )

    if not imports:
        raise ValueError("No valid audio files provided")

    # --- WAAPI call ---
    args = {
        "importOperation": import_operation,  # "useExisting" / "createNew" / "replaceExisting"
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

    Returns the created object as a dict (e.g. {'id': '{GUID}', 'name': ...}).
    """
    try:  
        return waapi_call(
                "ak.wwise.core.object.create",
                {
                 "parent": parent_id,          # WAQL or back-slash path
                 "type":   child_type,           # always "WorkUnit" for both cases
                 "name":   child_name,           # requested name for new work or folder 
                 "onNameConflict": on_conflict   # "fail", "rename", "replace", "merge") 
                }
        ) 
    
    except Exception as e:
        raise RuntimeError(f"WAAPI error: {e}")

def create_blend_track(
    blend_container_path: str,
    blend_track_name: str
) -> dict:
    """
    Creates a Blend Track inside a Blend Container.
    """

    return waapi_call("ak.wwise.core.blendContainer.addTrack", {
        "object": blend_container_path,
        "name": blend_track_name
    })

# ==============================================================================
#                   Deleting Objects in Wwise
# ==============================================================================

def delete_object(object_ref: str) -> dict:
    """
    Delete a Wwise object by GUID, path, or qualified name.

    Example object_ref values:
    - "\\Actor-Mixer Hierarchy\\Default Work Unit\\MySound"
    - "{A076AA65-B71A-45BB-8841-5A20C52CE727}"
    - "Event:Play_Footstep"

    Returns the WAAPI response dict.
    """
    if not object_ref or not isinstance(object_ref, str) or not object_ref.strip():
        raise WwiseValidationError("object_ref must be a non-empty string.")

    try:
        response = waapi_call("ak.wwise.core.object.delete", {
            "object": object_ref.strip()
        })

        if response is None:
            raise WwiseApiError(
                "WAAPI returned None when deleting object",
                operation="ak.wwise.core.object.delete",
                details={"object_ref": object_ref}
            )

        return response

    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error deleting object: {str(e)}",
            operation="ak.wwise.core.object.delete",
            details={
                "error_type": type(e).__name__,
                "object_ref": object_ref
            }
        )
    
# ==============================================================================
#                           Undo & Transaction
# ==============================================================================

def begin_undo_group() -> dict:
    """
    Opens a new undo group in Wwise. All subsequent authoring operations
    will be grouped together and can be rolled back atomically.

    Returns the WAAPI response dict.
    """
    try:
        response = waapi_call("ak.wwise.core.undo.beginGroup", {})

        if response is None:
            raise WwiseApiError(
                "WAAPI returned None when opening undo group",
                operation="ak.wwise.core.undo.beginGroup",
                details={}
            )

        return response

    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error opening undo group: {str(e)}",
            operation="ak.wwise.core.undo.beginGroup",
            details={"error_type": type(e).__name__}
        )


def end_undo_group(display_name: str) -> dict:
    """
    Closes the current undo group in Wwise, committing all grouped operations.

    Args:
        display_name (str) - Label shown in the Wwise undo history.

    Returns the WAAPI response dict.
    """
    if not display_name or not isinstance(display_name, str) or not display_name.strip():
        raise WwiseValidationError("display_name must be a non-empty string.")

    try:
        response = waapi_call("ak.wwise.core.undo.endGroup", {
            "displayName": display_name.strip()
        })

        if response is None:
            raise WwiseApiError(
                "WAAPI returned None when closing undo group",
                operation="ak.wwise.core.undo.endGroup",
                details={"display_name": display_name}
            )

        return response

    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error closing undo group: {str(e)}",
            operation="ak.wwise.core.undo.endGroup",
            details={
                "error_type": type(e).__name__,
                "display_name": display_name
            }
        )


def cancel_undo_group() -> dict:
    """
    Cancels the current undo group

    Returns the WAAPI response dict.
    """
    try:
        response = waapi_call("ak.wwise.core.undo.cancelGroup", {})

        if response is None:
            raise WwiseApiError(
                "WAAPI returned None when cancelling undo group",
                operation="ak.wwise.core.undo.cancelGroup",
                details={}
            )

        return response

    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error cancelling undo group: {str(e)}",
            operation="ak.wwise.core.undo.cancelGroup",
            details={"error_type": type(e).__name__}
        )

def undo() -> dict:
    """
    Undoes the last operation in Wwise, equivalent to pressing Ctrl+Z.

    Returns the WAAPI response dict.
    """
    try:
        response = waapi_call("ak.wwise.core.undo.undo", {})

        if response is None:
            raise WwiseApiError(
                "WAAPI returned None when undoing operation",
                operation="ak.wwise.core.undo.undo",
                details={}
            )

        return response

    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Unexpected error undoing operation: {str(e)}",
            operation="ak.wwise.core.undo.undo",
            details={"error_type": type(e).__name__}
        )

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

ATTENUATION_PROPERTY_HELP = """
Attenuation (WAAPI property names)

Radius Max — RadiusMax
  • Maximum distance of the attenuation (world units).
  • Real64, default 100.0, range [1, 100000000].

Cone Use — ConeUse
  • Enable/disable cone attenuation.
  • bool.

Cone max attenuation — ConeAttenuation
  • Additional attenuation applied outside the cone.
  • Real64 (dB), default -6.0, range [-200, 0].

Cone inner angle — ConeInnerAngle
  • Inner cone angle in degrees.
  • int32, default 90, range [0, 360].

Cone outer angle — ConeOuterAngle
  • Outer cone angle in degrees.
  • int32, default 245, range [0, 360].

Cone LPF — ConeLowPassFilterValue
  • Low-pass filter applied outside the cone.
  • int32, range [0, 100].

Cone HPF — ConeHighPassFilterValue
  • High-pass filter applied outside the cone.
  • int32, range [0, 100].

Height Spread — HeightSpreadEnable
  • Enable height spread behavior.
  • bool.

OverrideColor - OverrideColor
  • Set this property to true first or setting Color will not work. 
  • bool [True, False]

Color — Color
  • UI color index for the attenuation object. Make sure OverrideColor is set to True first!
  • int16, default 0, range [0, 26].

RTPC List — RTPC
  • RTPC list on the attenuation object.
  • List of RTPC objects; manipulated via ak.wwise.core.object.set / setAttenuationCurve.
"""

SOUND_PROPERTY_HELP = """
Sound (WAAPI property names)

--- Positioning / Attenuation ----------------------------------------

3D Position — 3DPosition
  • 0 = Emitter
  • 1 = Emitter with Automation
  • 2 = Listener with Automation

3D Spatialization — 3DSpatialization
  • 0 = None
  • 1 = Position
  • 2 = Position + Orientation

Attenuation (ShareSet / Custom) — Attenuation
  • Reference to an Attenuation object (ShareSet or custom instance).

Distance Scaling % — AttenuationDistanceScaling
  • Scale for attenuation distances.
  • Real32, default 1.0, range [0.01, 100].

Enable Attenuation — EnableAttenuation
  • Toggle use of attenuation on this Sound.
  • bool.

Listener Relative Routing — ListenerRelativeRouting
  • Required to use Attenuation, game/aux sends, etc.
  • bool.

Hold Emitter Position and Orientation — HoldEmitterPositionOrientation
  • Lock emitter transform while playing.
  • bool.

Hold Listener Orientation — HoldListenerOrientation
  • Lock listener orientation relative to emitter.
  • bool.


--- Core Mixing (per-Sound voice) -----------------------------------

Voice Volume — Volume
  • dB gain at the voice.
  • Real64, range [-200, 200].

Voice LPF — Lowpass
  • Voice low-pass filter.
  • int16, range [0, 100].

Voice HPF — Highpass
  • Voice high-pass filter.
  • int16, range [0, 100].

Make-Up Gain — MakeUpGain
  • Extra gain used with HDR envelope.
  • Real64, range [-96, 96].


--- Playback / Looping / Limits -------------------------------------

Initial Delay — InitialDelay
  • Delay before playback (seconds).
  • Real64, range [0, 3600].

Loop — IsLoopingEnabled
  • Enable/disable looping.
  • bool.

Infinite Loop — IsLoopingInfinite
  • If true, loop indefinitely; otherwise use LoopCount.
  • bool.

No. of Loops — LoopCount
  • Number of loops when Infinite is off.
  • int32, default 2, range [1, 32767].

Virtual Voice Behavior — BelowThresholdBehavior
  • 0 = Continue to play
  • 1 = Kill voice
  • 2 = Send to virtual voice
  • 3 = Kill if finite else virtual

Limitation Scope — IsGlobalLimit
  • 0 = Per game object
  • 1 = Globally

Limit Sound Instances (Enable) — UseMaxSoundPerInstance
  • Toggle instance limiting.
  • bool.

Sound Instance Limit — MaxSoundPerInstance
  • Max simultaneous voices (when limiting enabled).
  • int16, default 50, range [1, 1000].

When Priority is Equal — MaxReachedBehavior
  • 0 = Discard oldest instance
  • 1 = Discard newest instance

On Return to Physical Voice — VirtualVoiceQueueBehavior
  • 0 = Play from beginning
  • 1 = Play from elapsed time
  • 2 = Resume


--- Streaming / Voice Behavior --------------------------------------

Stream — IsStreamingEnabled
  • Use streaming for this source.
  • bool.

Non-Cachable — IsNonCachable
  • Prevents caching converted media.
  • bool.

Zero Latency — IsZeroLatency
  • Bypass look-ahead / scheduling to minimize latency.
  • bool.

Is Voice — IsVoice
  • Mark as a voice (affects certain profiling/mixing behavior).
  • bool.


--- Routing / Busses / Reflections ----------------------------------

Output Bus — OutputBus
  • Bus reference used by this Sound.
  • Reference type: Bus.

Early Reflections Aux Send — ReflectionsAuxSend
  • Aux bus used for early reflections.
  • Reference type: AuxBus.

Early Reflections Send Volume — ReflectionsVolume
  • Send level to ReflectionsAuxSend.
  • Real64, range [-200, 200].


--- Aux Sends (Game-defined) ----------------------------------------

Use Game-Defined Auxiliary Sends — UseGameAuxSends
  • Enable routing to game-defined aux sends.
  • bool.

Game Aux Sends Volume — GameAuxSendVolume
  • Master volume for game-defined sends.
  • Real64, range [-200, 200].

Game Aux Sends LPF — GameAuxSendLPF
  • Low-pass on game-defined sends.
  • int16, range [0, 100].

Game Aux Sends HPF — GameAuxSendHPF
  • High-pass on game-defined sends.
  • int16, range [0, 100].


--- Aux Sends (User-defined 0-3) ------------------------------------

User Aux Send 0-3 — UserAuxSend0..3
  • Per-slot aux bus references.
  • Type: AuxBus.

User Aux Volume 0-3 — UserAuxSendVolume0..3
  • Send volume per aux slot.
  • Real64, range [-200, 200].

User Aux LPF 0-3 — UserAuxSendLPF0..3
  • Low-pass per aux slot.
  • int16, range [0, 100].

User Aux HPF 0-3 — UserAuxSendHPF0..3
  • High-pass per aux slot.
  • int16, range [0, 100].


--- HDR & Loudness Normalization ------------------------------------

HDR Active Range — HdrActiveRange
  • HDR window range in dB.
  • Real64, range [0, 96].

Enable Envelope Tracking — HdrEnableEnvelope
  • Enables HDR envelope logic.
  • bool.

HDR Envelope Sensitivity — HdrEnvelopeSensitivity
  • Sensitivity of HDR envelope.
  • Real64, range [0, 100].

Enable Loudness Normalization — EnableLoudnessNormalization
  • Toggle loudness normalization.
  • bool.

Loudness Normalization Target — LoudnessNormalizationTarget
  • Target loudness in LUFS.
  • Real64, default -23, range [-96, 0].

Loudness Normalization Type — LoudnessNormalizationType
  • 0 = Integrated
  • 1 = Momentary Max


--- Misc -------------------------------------------------------------

Inclusion — Inclusion
  • Whether this object is included in the SoundBank generation.
  • bool.

OverrideColor - OverrideColor
    • Set this property to true first or setting Color will not work. 
    • bool [True, False]

Color — Color
  • UI color index for the Sound object. Make sure OverrideColor is set to True first!
  • int16, range [0, 26].

Weight — Weight
  • Weight used in containers (Random, Sequence, etc.).
  • Real64, default 50, range [0.001, 100].

Metadata list — Metadata
  • List of Metadata objects associated with this Sound.
"""

def get_all_property_name_valid_values() -> str: 
    return RANDOM_CONTAINER_PROPERTY_HELP + ATTENUATION_PROPERTY_HELP + SOUND_PROPERTY_HELP

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


def _reject_at_prefixed(name):
    """Property names are passed without the leading '@'; the wrapper adds it.
    A caller-supplied '@' would produce '@@Name'. Also guards type, because the
    create_* loops pass dict keys straight in (a non-str key would otherwise
    blow up on .startswith with a raw AttributeError)."""
    if not isinstance(name, str) or not name.strip():
        raise WwiseValidationError(f"property name must be a non-empty string, got {name!r}")
    if name.startswith("@"):
        raise WwiseValidationError(
            f"property name must not include the leading '@' (got {name!r}); the wrapper adds it"
        )


_OBJECT_SET_NAME_CONFLICT_MODES = frozenset({"fail", "rename", "replace", "merge"})


def add_effect_to_object(
    object_path: str,
    effect_ref: str,
    *,
    list_mode: str = "append",
) -> dict:
    """
    Insert an Effect/ShareSet reference into the @Effects list of a
    Bus, ActorMixer, or Sound via ak.wwise.core.object.set.

    Parameters
    ----------
    object_path : str
        Path/GUID of the host object (Bus, ActorMixer, etc).
    effect_ref : str
        Path or GUID of an existing Effect or ShareSet to insert.
    list_mode : str
        'append' (default) appends a new EffectSlot at the end.
        'replaceAll' replaces the entire @Effects list with this entry.

    WAAPI has no insert-at-index. To target a specific slot index,
    call with list_mode='replaceAll' and supply the full ordered list
    via a higher-level helper (out of scope here).

    Returns
    -------
    dict
        Raw WAAPI response from ak.wwise.core.object.set; shape
        `{"objects": [...]}` per the WAAPI object.set schema.
    """
    if not isinstance(object_path, str) or not object_path.strip():
        raise WwiseValidationError("object_path must be a non-empty string")
    if not isinstance(effect_ref, str) or not effect_ref.strip():
        raise WwiseValidationError("effect_ref must be a non-empty string")
    if list_mode not in _OBJECT_SET_LIST_MODES:
        raise WwiseValidationError(
            f"list_mode must be one of {sorted(_OBJECT_SET_LIST_MODES)}, "
            f"got {list_mode!r}"
        )

    args = {
        "objects": [
            {
                "object": object_path,
                "@Effects": [
                    {"type": "EffectSlot", "name": "", "@Effect": effect_ref}
                ],
            }
        ],
        "onNameConflict": "merge",
        "listMode": list_mode,
    }

    try:
        response = waapi_call("ak.wwise.core.object.set", args)
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to add effect to object: {e}",
            operation="ak.wwise.core.object.set",
            details={
                "error_type": type(e).__name__,
                "object_path": object_path,
                "effect_ref": effect_ref,
                "list_mode": list_mode,
            },
        )

    if response is None:
        raise WwiseApiError(
            "WAAPI returned None when adding effect to object",
            operation="ak.wwise.core.object.set",
            details={"object_path": object_path, "effect_ref": effect_ref},
        )

    return response


def create_effect_share_set(
    parent_path: str,
    name: str,
    class_id: int,
    *,
    properties: dict[str, int | bool | float | str] | None = None,
    on_name_conflict: str = "rename",
) -> dict:
    """
    Create a Custom Effect / Effect ShareSet under `parent_path` (typically
    `\\Effects\\Default Work Unit\\<folder>`) with the given plug-in classId.

    Plug-in classId values are defined by the Wwise plug-in (see WAAPI
    `wobjects_index`). Caller supplies the value; this wrapper does not
    look them up.

    Parameters
    ----------
    parent_path : str
        Project path of the parent Work Unit or Folder.
    name : str
        Name of the new ShareSet.
    class_id : int
        Plug-in classId.
    properties : dict | None
        Optional initial properties: each key becomes an @<Key> accessor on
        the new Effect.
    on_name_conflict : str
        'fail' | 'rename' | 'replace' | 'merge'. Default 'rename'.

    Returns
    -------
    dict
        The created ShareSet, unwrapped from the WAAPI response. Shape:
        `{"id": "<guid>", "name": "<resolved name>", "path": "<project path>",
        "type": "Effect"}` (fields requested via `options.return`). The raw
        WAAPI response from `object.set` nests the new ShareSet at
        `response["objects"][0]["children"][0]`; this wrapper returns the
        child directly so callers can chain off `$last.id` / `$last.path`
        in the plan executor.
    """
    if not isinstance(parent_path, str) or not parent_path.strip():
        raise WwiseValidationError("parent_path must be a non-empty string")
    if not isinstance(name, str) or not name.strip():
        raise WwiseValidationError("name must be a non-empty string")
    if not isinstance(class_id, int) or isinstance(class_id, bool):
        raise WwiseValidationError("class_id must be an int")
    if class_id < 0 or class_id > 0xFFFFFFFF:
        raise WwiseValidationError(
            f"class_id must fit in WAAPI unsigned 32-bit range [0, 0xFFFFFFFF], got {class_id}"
        )
    if properties is not None and not isinstance(properties, dict):
        raise WwiseValidationError("properties must be a dict if provided")
    if on_name_conflict not in _OBJECT_SET_NAME_CONFLICT_MODES:
        raise WwiseValidationError(
            f"on_name_conflict must be one of {sorted(_OBJECT_SET_NAME_CONFLICT_MODES)}, "
            f"got {on_name_conflict!r}"
        )

    child: dict = {"type": "Effect", "name": name, "classId": class_id}
    for prop_name, prop_value in (properties or {}).items():
        _reject_at_prefixed(prop_name)
        child[f"@{prop_name}"] = prop_value

    args = {
        "objects": [{"object": parent_path, "children": [child]}],
        "onNameConflict": on_name_conflict,
    }

    try:
        response = waapi_call(
            "ak.wwise.core.object.set",
            args,
            options={"return": ["id", "name", "path", "type"]},
        )
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to create Effect ShareSet: {e}",
            operation="ak.wwise.core.object.set",
            details={
                "error_type": type(e).__name__,
                "parent_path": parent_path,
                "name": name,
                "class_id": class_id,
            },
        )

    if response is None:
        raise WwiseApiError(
            "WAAPI returned None when creating Effect ShareSet",
            operation="ak.wwise.core.object.set",
            details={"parent_path": parent_path, "name": name},
        )

    # WAAPI mirrors the request shape: objects[0] is the parent we called
    # object.set on, and the created ShareSet sits at objects[0].children[0].
    # The project's $last.<attr> plan resolver only walks one dict level, so
    # callers that chain off the response need flat fields. Unwrap the child
    # explicitly so $last.id / $last.path resolve to the new ShareSet.
    try:
        created = response["objects"][0]["children"][0]
    except (KeyError, IndexError, TypeError) as e:
        raise WwiseApiError(
            f"Effect ShareSet was created but the WAAPI response shape was "
            f"unexpected (could not locate objects[0].children[0]): {e}",
            operation="ak.wwise.core.object.set",
            details={
                "error_type": type(e).__name__,
                "parent_path": parent_path,
                "name": name,
                "raw_response": response,
            },
        )

    return created


def set_plugin_property(
    object_path: str,
    property_name: str,
    value: int | bool | float | str,
    *,
    platform: str | None = None,
) -> dict:
    """
    Set an Effect plug-in property via ak.wwise.core.object.set using the
    @<PropertyName> accessor. Use this for Effect plug-in properties (Steam
    Audio Spatializer Reflections / Pathing / AirAbsorption etc.) that the
    older setProperty endpoint silently rejects.

    Parameters
    ----------
    object_path : str
        Project path or GUID of the object whose property is being set.
    property_name : str
        WAAPI property name *without* the leading '@' (e.g. 'Reflections').
        The function adds the '@' prefix.
    value : int | bool | float | str
        The new value. None is rejected (use the existing property removal
        endpoints if you need to clear a reference).
    platform : str | None
        Optional platform unique name or GUID. When omitted, the change
        applies to all linked platforms.
    """
    if not isinstance(object_path, str) or not object_path.strip():
        raise WwiseValidationError("object_path must be a non-empty string")
    if not isinstance(property_name, str) or not property_name.strip():
        raise WwiseValidationError("property_name must be a non-empty string")
    _reject_at_prefixed(property_name)
    if value is None:
        raise WwiseValidationError("value cannot be None")

    obj: dict = {"object": object_path, f"@{property_name}": value}
    if platform is not None:
        obj["platform"] = platform

    args = {"objects": [obj], "onNameConflict": "merge"}

    try:
        response = waapi_call("ak.wwise.core.object.set", args)
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to set plug-in property: {e}",
            operation="ak.wwise.core.object.set",
            details={
                "error_type": type(e).__name__,
                "object_path": object_path,
                "property_name": property_name,
                "platform": platform,
            },
        )

    return _require_non_none(response, "ak.wwise.core.object.set")


_RTPC_CURVE_SHAPES = frozenset({
    "Constant", "Linear",
    "Log3", "Log2", "Log1",
    "InvertedSCurve", "SCurve",
    "Exp1", "Exp2", "Exp3",
})


def set_rtpc_curve(
    object_path: str,
    property_name: str,
    control_input_ref: str,
    points: list[dict],
    *,
    platform: str | None = None,
) -> dict:
    """
    Bind a ControlInput (Game Parameter, Modulator, or MIDI) to a target
    property on an object via the @RTPC list, defining the curve with the
    given breakpoint array.

    Each point is a dict with keys 'x', 'y', and 'shape'. Shape must be one
    of: 'Constant', 'Linear', 'Log3', 'Log2', 'Log1', 'InvertedSCurve',
    'SCurve', 'Exp1', 'Exp2', 'Exp3'.

    The target property can be any settable property including Effect
    plug-in properties (Steam Audio Spatializer Reflections Mix Level etc.)
    that the older setProperty endpoint silently rejects.

    Returns
    -------
    dict
        Raw WAAPI response from ak.wwise.core.object.set.
    """
    if not isinstance(object_path, str) or not object_path.strip():
        raise WwiseValidationError("object_path must be a non-empty string")
    if not isinstance(property_name, str) or not property_name.strip():
        raise WwiseValidationError("property_name must be a non-empty string")
    _reject_at_prefixed(property_name)
    if not isinstance(control_input_ref, str) or not control_input_ref.strip():
        raise WwiseValidationError("control_input_ref must be a non-empty string")
    if not points:
        raise WwiseValidationError("points must be a non-empty list")

    normalized: list[dict] = []
    for i, p in enumerate(points):
        if not isinstance(p, dict) or "x" not in p or "y" not in p or "shape" not in p:
            raise WwiseValidationError(
                f"point at index {i} must be a dict with keys 'x', 'y', 'shape'"
            )
        # bool is a subclass of int in Python; reject it explicitly to avoid silent True/False coords
        for axis in ("x", "y"):
            v = p[axis]
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise WwiseValidationError(
                    f"point at index {i}: {axis!r} must be a number, got {type(v).__name__}"
                )
            if not math.isfinite(float(v)):
                raise WwiseValidationError(
                    f"point at index {i}: {axis!r} must be finite, got {v!r}"
                )
        if p["shape"] not in _RTPC_CURVE_SHAPES:
            raise WwiseValidationError(
                f"point at index {i}: shape must be one of "
                f"{sorted(_RTPC_CURVE_SHAPES)}, got {p['shape']!r}"
            )
        normalized.append({"x": p["x"], "y": p["y"], "shape": p["shape"]})

    obj: dict = {
        "object": object_path,
        "@RTPC": [
            {
                "type": "RTPC",
                "name": "",
                "@PropertyName": property_name,
                "@ControlInput": control_input_ref,
                "@Curve": {"type": "Curve", "points": normalized},
            }
        ],
    }
    if platform is not None:
        obj["platform"] = platform

    args = {"objects": [obj], "onNameConflict": "merge"}
    # @RTPC list has SupportListOperations="false" in WObjects.xml; omit listMode.

    try:
        response = waapi_call("ak.wwise.core.object.set", args)
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to set RTPC curve: {e}",
            operation="ak.wwise.core.object.set",
            details={
                "error_type": type(e).__name__,
                "object_path": object_path,
                "property_name": property_name,
                "control_input_ref": control_input_ref,
                "point_count": len(points),
            },
        )

    return _require_non_none(response, "ak.wwise.core.object.set")


def create_source_plugin(
    parent_path: str,
    name: str,
    class_id: int,
    *,
    properties: dict[str, int | bool | float | str] | None = None,
    language: str | None = None,
    on_name_conflict: str = "rename",
) -> dict:
    """
    Create a Source plug-in (Sine, Tone Generator, Silence, SoundSeed Air,
    etc.) as a child of a Sound or Voice object.

    Parameters
    ----------
    parent_path : str
        Path/GUID of the parent Sound or Voice object.
    name : str
        Name of the new Source child.
    class_id : int
        Plug-in classId (see WAAPI wobjects_index).
    properties : dict | None
        Optional initial property values; each key becomes an @<Key>
        accessor on the new Source.
    language : str | None
        Required for Voice parents (e.g. 'English(US)', 'Japanese'). When set,
        the child uses `type: "Source"` per WAAPI Voice schema. Omit for Sound
        parents: the child then uses `type: "SourcePlugin"` per WAAPI Sound
        schema. The wrapper picks the correct type based on whether `language`
        is supplied.
    on_name_conflict : str
        'fail' | 'rename' | 'replace' | 'merge'. Default 'rename'.

    Returns
    -------
    dict
        The created Source, unwrapped from the WAAPI response. Shape:
        `{"id": "<guid>", "name": "<resolved name>", "path": "<project path>",
        "type": "Source" | "SourcePlugin"}` (fields requested via
        `options.return`). The raw WAAPI response nests the new Source at
        `response["objects"][0]["children"][0]`; this wrapper returns the
        child directly so callers can chain off `$last.id` / `$last.path`
        in the plan executor.
    """
    if not isinstance(parent_path, str) or not parent_path.strip():
        raise WwiseValidationError("parent_path must be a non-empty string")
    if not isinstance(name, str) or not name.strip():
        raise WwiseValidationError("name must be a non-empty string")
    if not isinstance(class_id, int) or isinstance(class_id, bool):
        raise WwiseValidationError("class_id must be an int")
    if class_id < 0 or class_id > 0xFFFFFFFF:
        raise WwiseValidationError(
            f"class_id must fit in WAAPI unsigned 32-bit range [0, 0xFFFFFFFF], got {class_id}"
        )
    if language is not None and (not isinstance(language, str) or not language.strip()):
        raise WwiseValidationError("language must be a non-empty string when provided")
    if properties is not None and not isinstance(properties, dict):
        raise WwiseValidationError("properties must be a dict if provided")
    if on_name_conflict not in _OBJECT_SET_NAME_CONFLICT_MODES:
        raise WwiseValidationError(
            f"on_name_conflict must be one of {sorted(_OBJECT_SET_NAME_CONFLICT_MODES)}, "
            f"got {on_name_conflict!r}"
        )

    # WAAPI Sound parents take type=SourcePlugin (schema lines 1399-1431, 1676-1697).
    # Voice parents take type=Source with a required language field (schema lines 922-948).
    child_type = "Source" if language is not None else "SourcePlugin"

    child: dict = {"type": child_type, "name": name, "classId": class_id}
    if language is not None:
        child["language"] = language
    for prop_name, prop_value in (properties or {}).items():
        _reject_at_prefixed(prop_name)
        child[f"@{prop_name}"] = prop_value

    args = {
        "objects": [{"object": parent_path, "children": [child]}],
        "onNameConflict": on_name_conflict,
    }

    try:
        response = waapi_call(
            "ak.wwise.core.object.set",
            args,
            options={"return": ["id", "name", "path", "type"]},
        )
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to create Source plug-in: {e}",
            operation="ak.wwise.core.object.set",
            details={
                "error_type": type(e).__name__,
                "parent_path": parent_path,
                "name": name,
                "class_id": class_id,
                "language": language,
            },
        )

    if response is None:
        raise WwiseApiError(
            "WAAPI returned None when creating Source plug-in",
            operation="ak.wwise.core.object.set",
            details={"parent_path": parent_path, "name": name},
        )

    # WAAPI mirrors the request shape: objects[0] is the parent Sound/Voice we
    # called object.set on, and the created Source sits at
    # objects[0].children[0]. The project's $last.<attr> plan resolver only
    # walks one dict level, so chainable callers need flat fields. Unwrap the
    # child so $last.id / $last.path resolve to the new Source.
    try:
        created = response["objects"][0]["children"][0]
    except (KeyError, IndexError, TypeError) as e:
        raise WwiseApiError(
            f"Source plug-in was created but the WAAPI response shape was "
            f"unexpected (could not locate objects[0].children[0]): {e}",
            operation="ak.wwise.core.object.set",
            details={
                "error_type": type(e).__name__,
                "parent_path": parent_path,
                "name": name,
                "raw_response": response,
            },
        )

    return created


_PROFILER_CURSORS = frozenset({"user", "capture"})


def _validate_profiler_time(time: int | str) -> None:
    """Reject anything that is not a non-negative int or 'user' / 'capture'."""
    if isinstance(time, bool):
        raise WwiseValidationError(
            f"time must be int (ms) or one of {sorted(_PROFILER_CURSORS)}, got bool"
        )
    if isinstance(time, str):
        if time not in _PROFILER_CURSORS:
            raise WwiseValidationError(
                f"time string must be one of {sorted(_PROFILER_CURSORS)}, got {time!r}"
            )
        return
    if not isinstance(time, int):
        raise WwiseValidationError(
            f"time must be int (ms) or a profiler cursor string, got {type(time).__name__}"
        )
    if time < 0:
        raise WwiseValidationError(f"time must be >= 0 ms, got {time}")


def profiler_start_capture() -> dict:
    """
    Start the Wwise Profiler capture and return the capture cursor time in ms.

    Preconditions
    -------------
    Wwise Authoring must be running (the profiler endpoints operate on an
    active Authoring session).

    Returns
    -------
    dict
        Raw WAAPI response: {"return": <int ms>}.
    """
    try:
        response = waapi_call("ak.wwise.core.profiler.startCapture", {})
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to start profiler capture: {e}",
            operation="ak.wwise.core.profiler.startCapture",
            details={"error_type": type(e).__name__},
        )
    return _require_non_none(response, "ak.wwise.core.profiler.startCapture")


def profiler_stop_capture() -> dict:
    """
    Stop the Wwise Profiler capture and return the cursor time at the end of
    the capture in milliseconds.

    Behavior when no capture is active is not specified by the WAAPI schema;
    treat it as undefined and verify in smoke (Task 1 step 4).

    Returns
    -------
    dict
        Raw WAAPI response: {"return": <int ms>}.
    """
    try:
        response = waapi_call("ak.wwise.core.profiler.stopCapture", {})
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to stop profiler capture: {e}",
            operation="ak.wwise.core.profiler.stopCapture",
            details={"error_type": type(e).__name__},
        )
    return _require_non_none(response, "ak.wwise.core.profiler.stopCapture")


def profiler_get_cursor_time(cursor: str = "capture") -> dict:
    """
    Return the current position of the specified profiler time cursor in ms.

    Parameters
    ----------
    cursor : str
        'user' (the User Time Cursor) or 'capture' (the Capture Time Cursor).
        Defaults to 'capture' for the common "what's playing right now" case.

    Returns
    -------
    dict
        Raw WAAPI response: {"return": <int ms>}.
    """
    if not isinstance(cursor, str) or cursor not in _PROFILER_CURSORS:
        raise WwiseValidationError(
            f"cursor must be one of {sorted(_PROFILER_CURSORS)}, got {cursor!r}"
        )
    try:
        response = waapi_call(
            "ak.wwise.core.profiler.getCursorTime",
            {"cursor": cursor},
        )
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to get profiler cursor time: {e}",
            operation="ak.wwise.core.profiler.getCursorTime",
            details={"error_type": type(e).__name__, "cursor": cursor},
        )
    return _require_non_none(response, "ak.wwise.core.profiler.getCursorTime")


_PROFILER_DATA_TYPES_2024_1 = frozenset({
    "cpu", "memory", "stream", "voices", "listener",
    "obstructionOcclusion", "markersNotification", "soundbanks",
    "loadedMedia", "preparedObjects", "preparedGameSyncs",
    "interactiveMusic", "streamingDevice", "meter", "auxiliarySends",
    "apiCalls", "spatialAudio", "spatialAudioRaycasting",
    "voiceInspector", "audioObjects", "gameSyncs",
})


_PROFILER_DATA_TYPE_MIN_VERSION = {
    "customerSupportData": (2025, 1),
}


_PROFILER_DATA_TYPES = (
    _PROFILER_DATA_TYPES_2024_1
    | frozenset(_PROFILER_DATA_TYPE_MIN_VERSION)
)


def _get_wwise_year_major() -> tuple[int, int]:
    response = _require_non_none(
        waapi_call("ak.wwise.core.getInfo", {}),
        "ak.wwise.core.getInfo",
    )
    version = response.get("version", {})
    try:
        return int(version["year"]), int(version["major"])
    except (KeyError, TypeError, ValueError) as e:
        raise WwiseValidationError(
            f"Could not determine connected Wwise version from getInfo response: {version!r}"
        ) from e


def _validate_profiler_data_type_versions(payload: list[dict]) -> None:
    requested_versioned = sorted(
        {
            entry["dataType"]
            for entry in payload
            if entry["dataType"] in _PROFILER_DATA_TYPE_MIN_VERSION
        }
    )
    if not requested_versioned:
        return

    current = _get_wwise_year_major()
    for data_type in requested_versioned:
        minimum = _PROFILER_DATA_TYPE_MIN_VERSION[data_type]
        if current < minimum:
            raise WwiseValidationError(
                f"{data_type!r} requires Wwise {minimum[0]}.{minimum[1]}+; "
                f"connected Wwise is {current[0]}.{current[1]}"
            )


def profiler_enable_data(data_types: list) -> dict:
    """
    Enable or disable specific profiler data type captures, overriding the
    user's Profiler preferences for the current session.

    Each item is either a bare string (enable defaults to True) or a
    (dataType, enable_bool) tuple/list.

    Critical
    --------
    'voiceInspector' must be in this list before any
    profiler_get_voice_contributions() call returns useful data — the local
    WAAPI schema for enableProfilerData carries an example titled
    "Enabling profiler data required for getVoiceContributions" that pins
    this dependency.

    Parameters
    ----------
    data_types : list[str | tuple[str, bool] | list]
        Items from the profilerDataType enum (see _PROFILER_DATA_TYPES).
        'customerSupportData' is available on Wwise 2025.1+ only; when
        requested, this wrapper checks ak.wwise.core.getInfo before sending
        enableProfilerData so Wwise 2024.1 sessions fail with a clear
        validation error instead of a WAAPI enum error.

    Returns
    -------
    dict
        Raw WAAPI response (empty dict on success).
    """
    if not isinstance(data_types, list) or not data_types:
        raise WwiseValidationError("data_types must be a non-empty list")

    payload: list[dict] = []
    for i, item in enumerate(data_types):
        if isinstance(item, str):
            dt, enable = item, None
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            dt, enable = item[0], item[1]
            if not isinstance(dt, str):
                raise WwiseValidationError(
                    f"data_types[{i}] first element must be str, got {type(dt).__name__}"
                )
            if not isinstance(enable, bool):
                raise WwiseValidationError(
                    f"data_types[{i}] second element must be bool, got {type(enable).__name__}"
                )
        else:
            raise WwiseValidationError(
                f"data_types[{i}] must be str or (str, bool) pair, got {type(item).__name__}"
            )
        if dt not in _PROFILER_DATA_TYPES:
            raise WwiseValidationError(
                f"data_types[{i}] unknown dataType {dt!r}; valid: {sorted(_PROFILER_DATA_TYPES)}"
            )
        entry: dict = {"dataType": dt}
        if enable is not None:
            entry["enable"] = enable
        payload.append(entry)

    _validate_profiler_data_type_versions(payload)

    try:
        response = waapi_call(
            "ak.wwise.core.profiler.enableProfilerData",
            {"dataTypes": payload},
        )
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to enable profiler data: {e}",
            operation="ak.wwise.core.profiler.enableProfilerData",
            details={"error_type": type(e).__name__, "data_types": payload},
        )
    return _require_non_none(response, "ak.wwise.core.profiler.enableProfilerData")


def _validate_uint32(value, name):
    """Schema is number >= 0; we also reject > uint32 max as a defensive ceiling
    because WAAPI pipeline IDs are 32-bit."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise WwiseValidationError(f"{name} must be an int")
    if value < 0 or value > 0xFFFFFFFF:
        raise WwiseValidationError(
            f"{name} must be a non-negative pipeline ID "
            f"(schema: number >= 0; defensive uint32 cap applied), got {value}"
        )


def _validate_return_fields(return_fields, allowed):
    if not isinstance(return_fields, list) or not return_fields:
        raise WwiseValidationError("return_fields must be a non-empty list when provided")
    bad = [f for f in return_fields if not isinstance(f, str) or f not in allowed]
    if bad:
        raise WwiseValidationError(
            f"return_fields contains unknown values {bad}; valid: {sorted(allowed)}"
        )


_VOICE_RETURN_FIELDS = frozenset({
    "pipelineID", "playingID", "soundID",
    "gameObjectID", "gameObjectName",
    "objectGUID", "objectName",
    "playTargetID", "playTargetGUID", "playTargetName",
    "baseVolume", "gameAuxSendVolume", "envelope", "normalizationGain",
    "lowPassFilter", "highPassFilter", "priority",
    "isStarted", "isVirtual", "isForcedVirtual",
})


def profiler_get_voices(
    time: int | str = "capture",
    *,
    voice_pipeline_id: int | None = None,
    return_fields: list[str] | None = None,
    timeout: float = 5.0,
) -> dict:
    """
    Retrieve voices active at a specific profiler capture time.

    Parameters
    ----------
    time : int | str
        Integer ms or one of 'user' / 'capture'. Defaults to 'capture'.
    voice_pipeline_id : int | None
        Optional uint32 to restrict the response to one voice.
    return_fields : list[str] | None
        Subset of _VOICE_RETURN_FIELDS. WAAPI defaults to pipelineID +
        gameObjectID + objectGUID when omitted.
    timeout : float
        WAAPI reply timeout. Default 5.0s (5x global default) because
        getVoices can pause briefly when the session is hot.

    Returns
    -------
    dict
        Raw WAAPI response: {"return": [{...voice}, ...]}.
    """
    timeout = _validate_timeout_seconds(timeout)
    _validate_profiler_time(time)

    if voice_pipeline_id is not None:
        _validate_uint32(voice_pipeline_id, "voice_pipeline_id")

    if return_fields is not None:
        _validate_return_fields(return_fields, _VOICE_RETURN_FIELDS)

    args: dict = {"time": time}
    if voice_pipeline_id is not None:
        args["voicePipelineID"] = voice_pipeline_id

    options = {"return": return_fields} if return_fields else None

    try:
        response = waapi_call(
            "ak.wwise.core.profiler.getVoices",
            args,
            options=options,
            timeout=timeout,
        )
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to get profiler voices: {e}",
            operation="ak.wwise.core.profiler.getVoices",
            details={
                "error_type": type(e).__name__,
                "time": time,
                "voice_pipeline_id": voice_pipeline_id,
                "return_fields": return_fields,
                "timeout": timeout,
            },
        )
    return _require_non_none(response, "ak.wwise.core.profiler.getVoices")


def profiler_get_voice_contributions(
    voice_pipeline_id: int,
    *,
    time: int | str = "capture",
    busses_pipeline_id: list[int] | None = None,
    timeout: float = 5.0,
) -> dict:
    """
    Retrieve the contribution tree (volume / LPF / HPF) for one voice path.

    Preconditions
    -------------
    profiler_enable_data must have included 'voiceInspector' for this
    session. Without it, the returned tree is empty.

    Parameters
    ----------
    voice_pipeline_id : int
        Pipeline ID of the voice. Obtain from profiler_get_voices.
        Validation: int + non-negative + capped at 0xFFFFFFFF. The WAAPI
        schema only requires `number >= 0`, but Wwise's internal AkPipelineID
        type is uint32, so the wrapper enforces uint32 as a defensive bound. Callers
        who need to bypass the cap (e.g. a hypothetical Wwise version
        that widens the type) should call waapi_call() directly.
    time : int | str
        Integer ms or one of 'user' / 'capture'. Defaults to 'capture'.
    busses_pipeline_id : list[int] | None
        Optional bus pipeline-ID chain identifying a wet path. Pass `[]`
        explicitly to request the dry path (schema:
        `ak.wwise.core.profiler.getVoiceContributions.json` describes empty array as the dry-path
        default). Omitting (`None`) leaves the field out of the args dict;
        WAAPI's behavior with an absent `bussesPipelineID` is not
        documented to equal the empty-array case, so callers that mean
        "dry path" should pass `[]` rather than rely on omission.
        Each entry has the same uint32 cap as voice_pipeline_id (same
        defensive rationale; same escape hatch).
    timeout : float
        WAAPI reply timeout. Default 5.0s.

    Returns
    -------
    dict
        Raw WAAPI response:
        {"return": {"volume": <db>, "LPF": <n>, "HPF": <n>,
                    "objects": [<voiceContributionsObject>, ...]}}.
        Each voiceContributionsObject has: name, volume, LPF, HPF,
        optional index (per-emitter ray ID), optional children (recursive),
        optional parameters[{propertyType, reason, driver, driverValue, value}].
    """
    timeout = _validate_timeout_seconds(timeout)
    _validate_uint32(voice_pipeline_id, "voice_pipeline_id")

    _validate_profiler_time(time)

    if busses_pipeline_id is not None:
        if not isinstance(busses_pipeline_id, list):
            raise WwiseValidationError("busses_pipeline_id must be a list when provided")
        for i, b in enumerate(busses_pipeline_id):
            _validate_uint32(b, f"busses_pipeline_id[{i}]")

    args: dict = {"voicePipelineID": voice_pipeline_id, "time": time}
    if busses_pipeline_id is not None:
        args["bussesPipelineID"] = busses_pipeline_id

    try:
        response = waapi_call(
            "ak.wwise.core.profiler.getVoiceContributions",
            args,
            timeout=timeout,
        )
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to get voice contributions: {e}",
            operation="ak.wwise.core.profiler.getVoiceContributions",
            details={
                "error_type": type(e).__name__,
                "voice_pipeline_id": voice_pipeline_id,
                "time": time,
                "busses_pipeline_id": busses_pipeline_id,
                "timeout": timeout,
            },
        )
    return _require_non_none(response, "ak.wwise.core.profiler.getVoiceContributions")


_AUDIO_OBJECT_RETURN_FIELDS = frozenset({
    # Full audioObjectReturnOptions return-field set, kept in sync with the
    # WAAPI getAudioObjects schema (no subsetting, to avoid schema drift).
    "busName", "effectPluginName", "audioObjectID", "busPipelineID",
    "gameObjectID", "gameObjectName", "audioObjectName",
    "instigatorPipelineID", "busID", "busGUID",
    "spatializationMode", "x", "y", "z",
    "spread", "focus", "channelConfig",
    "effectClassID", "effectIndex", "metadata",
    "rmsMeter", "peakMeter",
})


def profiler_get_audio_objects(
    time: int | str = "capture",
    *,
    bus_pipeline_id: int | None = None,
    return_fields: list[str] | None = None,
    timeout: float = 5.0,
) -> dict:
    """
    Retrieve Audio Objects in the post-mix pipeline at a profiler capture time.

    Candidate source for Effect plug-in name verification: the
    'effectPluginName' field on each audio object is documented as the
    plug-in identity. rmsMeter / peakMeter give non-silence signal in the
    same call.

    Parameters
    ----------
    time : int | str
        Integer ms or one of 'user' / 'capture'.
    bus_pipeline_id : int | None
        Optional uint32 to restrict the response to one bus's audio objects.
    return_fields : list[str] | None
        Subset of _AUDIO_OBJECT_RETURN_FIELDS. WAAPI default is
        audioObjectID + busPipelineID + instigatorPipelineID + effectClassID.

    Returns
    -------
    dict
        Raw WAAPI response: {"return": [{...audioObject}, ...]}.
    """
    timeout = _validate_timeout_seconds(timeout)
    _validate_profiler_time(time)

    if bus_pipeline_id is not None:
        _validate_uint32(bus_pipeline_id, "bus_pipeline_id")

    if return_fields is not None:
        _validate_return_fields(return_fields, _AUDIO_OBJECT_RETURN_FIELDS)

    args: dict = {"time": time}
    if bus_pipeline_id is not None:
        args["busPipelineID"] = bus_pipeline_id

    options = {"return": return_fields} if return_fields else None

    try:
        response = waapi_call(
            "ak.wwise.core.profiler.getAudioObjects",
            args,
            options=options,
            timeout=timeout,
        )
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to get profiler audio objects: {e}",
            operation="ak.wwise.core.profiler.getAudioObjects",
            details={
                "error_type": type(e).__name__,
                "time": time,
                "bus_pipeline_id": bus_pipeline_id,
                "return_fields": return_fields,
                "timeout": timeout,
            },
        )
    return _require_non_none(response, "ak.wwise.core.profiler.getAudioObjects")


_BUS_RETURN_FIELDS = frozenset({
    "pipelineID", "mixBusID", "objectGUID", "objectName",
    "gameObjectID", "gameObjectName", "deviceID",
    "volume", "downstreamGain",
    "voiceCount", "effectCount", "depth",
})


def profiler_get_busses(
    time: int | str = "capture",
    *,
    bus_pipeline_id: int | None = None,
    return_fields: list[str] | None = None,
    timeout: float = 5.0,
) -> dict:
    """
    Retrieve busses active at a specific profiler capture time.

    Complementary signal to get_voices: inspect bus voiceCount /
    effectCount / volume to cross-check that the expected bus routing is
    active. Bus identity follows the project's own bus hierarchy.

    Parameters
    ----------
    time : int | str
    bus_pipeline_id : int | None
    return_fields : list[str] | None
        Subset of _BUS_RETURN_FIELDS.

    Returns
    -------
    dict
        Raw WAAPI response: {"return": [{...bus}, ...]}.
    """
    timeout = _validate_timeout_seconds(timeout)
    _validate_profiler_time(time)

    if bus_pipeline_id is not None:
        _validate_uint32(bus_pipeline_id, "bus_pipeline_id")

    if return_fields is not None:
        _validate_return_fields(return_fields, _BUS_RETURN_FIELDS)

    args: dict = {"time": time}
    if bus_pipeline_id is not None:
        args["busPipelineID"] = bus_pipeline_id

    options = {"return": return_fields} if return_fields else None

    try:
        response = waapi_call(
            "ak.wwise.core.profiler.getBusses",
            args,
            options=options,
            timeout=timeout,
        )
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to get profiler busses: {e}",
            operation="ak.wwise.core.profiler.getBusses",
            details={
                "error_type": type(e).__name__,
                "time": time,
                "bus_pipeline_id": bus_pipeline_id,
                "return_fields": return_fields,
                "timeout": timeout,
            },
        )
    return _require_non_none(response, "ak.wwise.core.profiler.getBusses")


def profiler_get_rtpcs(
    time: int | str = "capture",
    *,
    timeout: float = 5.0,
) -> dict:
    """
    Retrieve RTPCs (Game Parameters / LFO / Time / Envelope / MIDI params)
    that are active at the given profiler capture time.

    The endpoint takes no return-field whitelist - the response shape is
    fixed by the WAAPI schema.

    Parameters
    ----------
    time : int | str
    timeout : float

    Returns
    -------
    dict
        Raw WAAPI response:
        {"return": [{"id": guid, "name": str,
                     "gameObjectId": int64,  # AK_INVALID_GAME_OBJECT for global
                     "value": number}]}.
    """
    timeout = _validate_timeout_seconds(timeout)
    _validate_profiler_time(time)
    try:
        response = waapi_call(
            "ak.wwise.core.profiler.getRTPCs",
            {"time": time},
            timeout=timeout,
        )
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to get profiler RTPCs: {e}",
            operation="ak.wwise.core.profiler.getRTPCs",
            details={"error_type": type(e).__name__, "time": time, "timeout": timeout},
        )
    return _require_non_none(response, "ak.wwise.core.profiler.getRTPCs")


def profiler_save_capture(file_path: str, *, timeout: float = 5.0) -> dict:
    """
    Save the current profiler capture to a .prof file.

    The WAAPI endpoint is ak.wwise.core.profiler.saveCapture (NOT
    saveProfilerCapture - the latter is a common mis-naming from older docs).

    Parameters
    ----------
    file_path : str
        Absolute path the Wwise Authoring process can write to. Typically
        ends with .prof.
    timeout : float, optional
        WAAPI call timeout in seconds. Defaults to 5.0; saving a .prof
        capture is disk I/O that can realistically exceed the WwiseSession
        default of 1.0s.

    Returns
    -------
    dict
        Empty dict on success.
    """
    timeout = _validate_timeout_seconds(timeout)
    if not isinstance(file_path, str) or not file_path.strip():
        raise WwiseValidationError("file_path must be a non-empty string")
    file_path = file_path.strip()
    if not Path(file_path).is_absolute():
        raise WwiseValidationError(
            f"file_path must be an absolute path (Wwise Authoring's cwd is its own install dir, not the caller's; relative paths land in unexpected locations or fail silently). Got {file_path!r}"
        )
    try:
        response = waapi_call(
            "ak.wwise.core.profiler.saveCapture",
            {"file": file_path},
            timeout=timeout,
        )
    except WwisePyLibError:
        raise
    except Exception as e:
        raise WwiseApiError(
            f"Failed to save profiler capture: {e}",
            operation="ak.wwise.core.profiler.saveCapture",
            details={"error_type": type(e).__name__, "file_path": file_path, "timeout": timeout},
        )
    return _require_non_none(response, "ak.wwise.core.profiler.saveCapture")
