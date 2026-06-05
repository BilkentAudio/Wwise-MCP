"""
WAAPI Client - Single Session Manager

This module maintains a single global WAAPI connection for the MCP server lifetime.
Thread-safe for multiple MCP tool invocations but supports only ONE Wwise session.

Not suitable for:
- Multi-tenant applications
- Connecting to multiple Wwise instances

"""

from waapi import WaapiClient
import threading
import time
import heapq
import queue
import logging
from typing import TypedDict, Optional


# Set up logger for this module
logger = logging.getLogger(__name__)

# Configuration constants
_URL = "ws://127.0.0.1:8080/waapi"
_DEFAULT_TIMEOUT = 1.0
_DISPATCHER_SHUTDOWN_TIMEOUT = 2.0
_QUEUE_CHECK_INTERVAL = 0.1
_MAX_QUEUE_SIZE = 100000

# Module-level state
_client = None
_dispatcher = None
_lock = threading.Lock()
_reconnecting = False 


class WaapiError(Exception):
    """Base exception for all WAAPI operations"""

class WaapiQueueFullError(WaapiError):
    """WAAPI queue is full - backpressure limit reached"""
    def __init__(self, message: str, queue_size: int, max_size: int):
        super().__init__(message)
        self.queue_size = queue_size
        self.max_size = max_size

def waapi_call(
    uri: str, 
    args: dict | None = None, 
    options: dict | None = None,
    *,
    due_in: float | None = None,     # seconds from now (None = ASAP) 
    wait: bool = True,               # wait for result or fire-and-forget
    timeout: float = _DEFAULT_TIMEOUT):

    """
    Thread-safe WAAPI call.
    - If on dispatcher thread -> call client directly.
    - Else -> enqueue on dispatcher; optionally wait for result.
    - Can schedule for the future with due_in / due_at.
    """

    if due_in is not None and due_in < 0.0: 
        logger.error("Invalid due_in value: %s (must be >= 0.0)", due_in)
        raise ValueError("due_in value cannot be negative. Please pass in >= 0.0 value ranges for due_in.")

    global _client, _dispatcher, _reconnecting

    # Capture references under lock
    with _lock:
        if _reconnecting:
            raise ValueError(
                "WAAPI is reconnecting. Please retry in a moment."
            )
        
        if _client is None or _dispatcher is None:
            logger.error("WAAPI call attempted before connection established. URI: %s", uri)
            raise ValueError("WAAPI not connected. Call connect_to_waapi() first.")
                
        dispatcher = _dispatcher

        if not dispatcher.is_alive():
            logger.error("WAAPI dispatcher thread is not running. URI: %s", uri)
            raise ValueError("WAAPI dispatcher not running. Call connect_to_waapi() to restart.")

        is_dispatcher_thread = dispatcher.is_dispatcher_thread()

    # should never waapi call from dispatcher thread
    if is_dispatcher_thread:
        logger.error("waapi_call() invoked from dispatcher thread. URI: %s", uri)
        raise RuntimeError(
            "Cannot call waapi_call() from dispatcher thread. "
            "This indicates a design error - WAAPI calls should only come from MCP request handlers, "
            "not from within the dispatcher or callbacks."
        )
    
    # Schedule the call
    due_at = (time.monotonic() + due_in) if due_in else None
    
    if due_in:
        logger.debug("Scheduling WAAPI call. URI: %s, due_in: %.3fs, wait: %s", uri, due_in, wait)
    else:
        logger.debug("Scheduling immediate WAAPI call. URI: %s, wait: %s", uri, wait)
    
    req = dispatcher.enqueue(uri, args or {}, options, due_at=due_at, want_reply=wait)

    if not wait:
        logger.debug("Fire-and-forget call enqueued. URI: %s", uri)
        return None
    
    # Wait for result with proper timeout handling
    logger.debug("Waiting for WAAPI call result. URI: %s, timeout: %.3fs", uri, timeout)
    try:
        status, data = req["reply_q"].get(timeout=timeout)
    except queue.Empty:
        logger.warning("WAAPI call timed out. URI: %s, timeout: %.3fs", uri, timeout)
        raise TimeoutError(f"WAAPI call to '{uri}' timed out after {timeout}s")
    
    if status == "ok": 
        logger.debug("WAAPI call succeeded. URI: %s", uri)
        return data
    
    logger.error("WAAPI call failed. URI: %s, Error: %s", uri, str(data))
    raise data
    

def connect_to_waapi(): 
    """
    Reconnect to the Wwise Authoring API.
    
    Safely tears down any existing WAAPI connection and establishes a new one
    to the server specified by the global _URL. This function is thread-safe
    and will block concurrent waapi_call() attempts during reconnection.
    
    During reconnection:
    - Other threads calling waapi_call() will receive "WAAPI is reconnecting" errors
    - The old dispatcher thread is stopped gracefully
    - The old client connection is closed
    - A new client and dispatcher are created
    
    Raises:
        ValueError: If connection to the WAAPI server fails or already in progress
    """

    global _client, _dispatcher, _reconnecting  

    # Phase 1: Mark as reconnecting and capture old resources
    with _lock:
        if _reconnecting:
            logger.warning("Reconnection already in progress")
            raise ValueError("WAAPI reconnection already in progress")
        
        _reconnecting = True
        old_dispatcher = _dispatcher
        old_client = _client
        url = _URL

        # Clear globals immediately while holding lock
        _client = None
        _dispatcher = None
    
    # From here on, we MUST clear _reconnecting flag before returning/raising
    try:
        # Phase 2: Clean up old resources (can block, so outside lock)
        if old_dispatcher:
            try:
                old_dispatcher.stop()
                logger.debug("Old dispatcher stopped successfully")
            except Exception as e:
                logger.warning("Error stopping old dispatcher: %s", str(e), exc_info=True)
        
        if old_client: 
            try:
                old_client.disconnect()
                logger.debug("Old client disconnected successfully")
            except Exception as e:
                logger.warning("Error disconnecting old client: %s", str(e), exc_info=True)

        # Phase 3: Create new connection
        logger.debug("Creating new WaapiClient connection to %s", url)
        new_client = WaapiClient(url, allow_exception=True)
        logger.debug("WaapiClient created successfully")
        
        try:
            logger.debug("Creating and starting WaapiDispatcher")
            new_dispatcher = WaapiDispatcher(client=new_client)
            new_dispatcher.start()
            logger.debug("WaapiDispatcher started successfully")
            
            # Phase 4: Atomically update globals and clear reconnecting flag
            with _lock:
                _client = new_client
                _dispatcher = new_dispatcher
                _reconnecting = False
            
            logger.info("WAAPI reconnection completed successfully")
            
        except Exception as e:
            # Dispatcher creation/start failed - cleanup the client we just made
            logger.error("Failed to create/start WaapiDispatcher: %s", str(e), exc_info=True)
            try:
                new_client.disconnect()
                logger.debug("Cleaned up client after dispatcher failure")
            except Exception as cleanup_err:
                logger.warning("Failed to cleanup client after dispatcher failure: %s", 
                             str(cleanup_err), exc_info=True)
            raise
            
    except Exception as e:
        # Any failure during reconnection - ensure globals are None and flag is cleared
        with _lock:
            _client = None
            _dispatcher = None
            _reconnecting = False
        
        logger.error("WAAPI reconnection failed: %s", str(e), exc_info=True)
        raise
    
def disconnect_from_wwise_client():
    global _client, _dispatcher
    
    with _lock:
        if _dispatcher: 
            _dispatcher.stop()
        elif _client: 
            _client.disconnect()

# ==========================================================================================
#                       Timed priority queue (MPSC -> single consumer)
# ========================================================================================== 

class _Req(TypedDict):

    due_at: float
    uri: str
    args: dict
    options: dict | None
    reply_q: Optional[queue.Queue] 


class _TimedPQ:

    def __init__(self, max_size: int = _MAX_QUEUE_SIZE):
        self._pq = []
        self._cv = threading.Condition()
        self._seq = 0  # tie-breaker
        self._max_size = max_size

    def put(self, due_at: float, req: _Req):
        with self._cv:
            current_size = len(self._pq)
            if len(self._pq) >= self._max_size:
                raise WaapiQueueFullError(
                f"WAAPI queue full ({self._max_size} requests)",
                queue_size=current_size,  
                max_size=self._max_size 
            )
            
            heapq.heappush(self._pq, (due_at, self._seq, req))
            self._seq += 1
            self._cv.notify()
            
            # Log queue depth periodically (every 10 items to avoid spam)
            if len(self._pq) % 10 == 0 and len(self._pq) > 0:
                logger.debug("TimedPQ depth: %d requests", len(self._pq))

    def get_next_due(self, stop_flag: threading.Event) -> Optional[_Req]:
        with self._cv:
            while not stop_flag.is_set():  # Check stop flag each iteration
                if not self._pq:
                    self._cv.wait(timeout=_QUEUE_CHECK_INTERVAL)  # Wake up every 100ms to check
                    continue
                
                due_at, _, req = self._pq[0]
                wait = max(0.0, due_at - time.monotonic())
                
                if wait > 0:
                    # Wake up every 100ms OR when task is due (whichever is sooner)
                    self._cv.wait(timeout=min(wait, _QUEUE_CHECK_INTERVAL))
                    continue
                
                heapq.heappop(self._pq)
                return req
            
            logger.debug("TimedPQ get_next_due exiting due to stop flag")
            return None  # ← Stop flag was set, signal shutdown
        

# ==========================================================================================
#                               Dispatcher
# ==========================================================================================

class WaapiDispatcher:

    def __init__(self, *, client: WaapiClient, max_queue_size: int = _MAX_QUEUE_SIZE):
        self._pq = _TimedPQ(max_size=max_queue_size)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._client: Optional[WaapiClient] = client   # adopt here
        self._thread_id: Optional[int] = None
        logger.debug("WaapiDispatcher initialized")

    def start(self):
        if self._thread and self._thread.is_alive(): 
            logger.warning("Attempted to start dispatcher when already running")
            return
        
        logger.debug("Starting WaapiDispatcher thread")
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="WaapiDispatcher")
        self._thread.start()
        logger.info("WaapiDispatcher thread started")

    def stop(self, timeout=_DISPATCHER_SHUTDOWN_TIMEOUT):
        logger.info("Stopping WaapiDispatcher (timeout: %.1fs)", timeout)
        self._stop.set()
        
        if self._thread: 
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("WaapiDispatcher thread did not stop within timeout")
            else:
                logger.debug("WaapiDispatcher thread stopped successfully")
        
        try:
            if self._client: 
                logger.debug("Disconnecting WAAPI client")
                self._client.disconnect()
                logger.debug("WAAPI client disconnected")
        except Exception as e:
            logger.warning("Error disconnecting WAAPI client: %s", str(e), exc_info=True)
        
        self._client = None
        logger.info("WaapiDispatcher stopped")

    def is_dispatcher_thread(self) -> bool:
        return threading.get_ident() == self._thread_id
    
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def enqueue(self, uri: str, args: dict|None=None, options: dict|None=None,
                *, due_at: float|None=None, want_reply=False) -> _Req:
        req: _Req = {
            "due_at": due_at if due_at is not None else time.monotonic(),
            "uri": uri,
            "args": args or {},
            "options": options,
            "reply_q": (queue.Queue(maxsize=1) if want_reply else None),
        }
        self._pq.put(req["due_at"], req)
        return req

    def _run(self):
        self._thread_id = threading.get_ident()
        logger.info("WaapiDispatcher thread running (thread_id: %d)", self._thread_id)
        
        call_count = 0
        error_count = 0
        
        while not self._stop.is_set():
            req = self._pq.get_next_due(self._stop)
            
            if req is None:  # Stopped
                logger.info("WaapiDispatcher exiting (processed %d calls, %d errors)", 
                          call_count, error_count)
                break
            
            call_count += 1
            
            try:
                logger.debug("Executing WAAPI call #%d. URI: %s", call_count, req["uri"])
                if req["options"] is None:
                    result = self._client.call(req["uri"], req["args"])
                else:
                    result = self._client.call(
                        req["uri"],
                        req["args"],
                        options=req["options"],
                    )
                
                # Only put result if someone is waiting for it
                if req["reply_q"] is not None:
                    try:
                        req["reply_q"].put(("ok", result), block=False) 
                    except queue.Full:
                        logger.debug("Result discarded - caller already timed out. URI: %s", req["uri"])
                else:
                    logger.debug("WAAPI fire-and-forget call #%d succeeded. URI: %s", 
                               call_count, req["uri"])
                    
            except Exception as e:
                error_count += 1
                logger.error("WAAPI call #%d failed. URI: %s, Error: %s", 
                           call_count, req["uri"], str(e), exc_info=True)
                
                # Only put error if someone is waiting for it
                if req["reply_q"] is not None:
                    try:
                        req["reply_q"].put(("err", e), block=False)  
                    except queue.Full:
                        logger.debug("Error discarded - caller already timed out. URI: %s", req["uri"])
                else:
                    logger.warning("Fire-and-forget call #%d failed (exception swallowed). URI: %s", 
                                 call_count, req["uri"])
            
            # Log stats every 100 calls
            if call_count % 100 == 0:
                logger.info("WaapiDispatcher stats: %d calls processed, %d errors", 
                          call_count, error_count)
