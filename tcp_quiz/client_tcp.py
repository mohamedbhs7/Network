# tcp_client.py
"""
Threaded TCP client module used by Streamlit UI.
- Start a persistent client with start_client(username, host, port).
- send_answer(answer) to send framed 'answer:...' messages to server.
- get_state() returns a snapshot dict with current fields:
    { "connected", "username", "question", "options", "leaderboard", "feedback", "score", "game_started", "game_over", "messages" }
- stop_client() to close the socket and stop threads (optional).
"""

import socket
import threading
import queue
import time

DELIM = "\n"

# Module-level singleton state
_client_sock = None
_listener_thread = None
_send_queue = None
_recv_queue = None
_state_lock = threading.Lock()
_state = {
    "connected": False,
    "username": "",
    "question": "",
    "options": [],
    "leaderboard": {},
    "feedback": "",
    "score": 0,
    "game_started": False,
    "game_over": False,
    "messages": [],
}

_stop_event = threading.Event()


def _enqueue_recv(line):
    """Process raw server line into state (runs in listener thread)."""
    line = line.strip()
    if not line:
        return
    # Keep raw messages for debugging
    with _state_lock:
        _state["messages"].append(line)
    # Basic parsing
    if line.startswith("welcome:"):
        with _state_lock:
            _state["messages"].append(line.split("welcome:", 1)[1])
    elif line.startswith("start_quiz"):
        with _state_lock:
            _state["game_started"] = True
    elif line.startswith("question:"):
        payload = line.split("question:", 1)[1]
        parts = payload.split("|")
        with _state_lock:
            _state["question"] = parts[0]
            _state["options"] = parts[1:] if len(parts) > 1 else []
            _state["feedback"] = ""
    elif line.startswith("feedback:"):
        with _state_lock:
            _state["feedback"] = line.split("feedback:", 1)[1]
    elif line.startswith("leaderboard:"):
        payload = line.split("leaderboard:", 1)[1]
        lb = {}
        if payload:
            for entry in payload.split("|"):
                if ":" in entry:
                    u, p = entry.split(":", 1)
                    try:
                        lb[u] = int(p)
                    except:
                        lb[u] = 0
        with _state_lock:
            _state["leaderboard"] = lb
            if _state["username"] in lb:
                _state["score"] = lb[_state["username"]]
    elif line.startswith("quiz_over:"):
        with _state_lock:
            _state["game_over"] = True
            _state["messages"].append(line.split("quiz_over:", 1)[1])
    elif line.startswith("error:"):
        with _state_lock:
            _state["messages"].append("ERROR: " + line.split("error:", 1)[1])
    else:
        # generic
        with _state_lock:
            _state["messages"].append(line)


def _listener(sock, recv_q: queue.Queue):
    """Listener thread: read bytes, split on DELIM, put lines into recv_q."""
    buffer = ""
    sock.settimeout(1.0)
    while not _stop_event.is_set():
        try:
            data = sock.recv(4096).decode()
            if not data:
                # Connection closed by server
                recv_q.put("error:Connection closed by server")
                break
            buffer += data
            while DELIM in buffer:
                line, buffer = buffer.split(DELIM, 1)
                recv_q.put(line)
        except socket.timeout:
            continue
        except Exception as e:
            recv_q.put(f"error:Listener exception: {e}")
            break
    # mark stopped
    try:
        sock.close()
    except:
        pass


def _sender(sock, send_q: queue.Queue):
    """Sender thread: take messages from send_q and send them framed."""
    while not _stop_event.is_set():
        try:
            msg = send_q.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            sock.sendall((msg + DELIM).encode())
        except Exception:
            # failed to send -> put error into recv queue so listener/main can see
            try:
                _recv_queue.put("error:Failed to send message")
            except:
                pass


def start_client(username, host="127.0.0.1", port=8888, timeout=5.0):
    """
    Start and connect the singleton client.
    Safe to call multiple times; if already running, returns True.
    """
    global _client_sock, _listener_thread, _send_queue, _recv_queue, _listener_thread, _send_thread

    if _state["connected"]:
        return True

    _stop_event.clear()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.setblocking(True)
    except Exception as e:
        with _state_lock:
            _state["messages"].append(f"error:Connect failed: {e}")
        return False

    # queues
    _send_queue = queue.Queue()
    _recv_queue = queue.Queue()

    # set module vars
    _client_sock = sock
    _send_thread = threading.Thread(target=_sender, args=(sock, _send_queue), daemon=True)
    _listener_thread = threading.Thread(target=_listener, args=(sock, _recv_queue), daemon=True)

    # set username and connected flag
    with _state_lock:
        _state["username"] = username
        _state["connected"] = True
        _state["messages"].append(f"Connected (local client) as {username}")

    # start threads
    _send_thread.start()
    _listener_thread.start()

    # send join message
    _send_queue.put(f"join:{username}")

    # start a small internal worker thread that drains recv_queue and applies to state
    def _drain_worker():
        while not _stop_event.is_set():
            try:
                line = _recv_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            # process the line (runs in this worker thread)
            _enqueue_recv(line)
        # cleanup on exit
    threading.Thread(target=_drain_worker, daemon=True).start()

    return True


def send_answer(answer):
    """Queue an 'answer:...' message to the server. Returns True if enqueued."""
    if not _state["connected"] or _client_sock is None or _send_queue is None:
        return False
    _send_queue.put(f"answer:{answer}")
    return True


def get_state():
    """Return a shallow copy snapshot of current state (safe to call from Streamlit)."""
    with _state_lock:
        return {
            "connected": _state["connected"],
            "username": _state["username"],
            "question": _state["question"],
            "options": list(_state["options"]),
            "leaderboard": dict(_state["leaderboard"]),
            "feedback": _state["feedback"],
            "score": _state["score"],
            "game_started": _state["game_started"],
            "game_over": _state["game_over"],
            "messages": list(_state["messages"][-20:]),
        }


def stop_client():
    """Stop the threads and close socket."""
    _stop_event.set()
    try:
        if _client_sock:
            _client_sock.close()
    except:
        pass
    with _state_lock:
        _state["connected"] = False
    return True
