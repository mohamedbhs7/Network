# server_tcp.py
"""
TCP quiz server (central broadcast model).
Messages are newline-delimited (DELIM = '\n') and simple string commands:
- Client -> Server:
    join:<username>\n
    answer:<option>\n     (option is exact option string as sent in question)
- Server -> Client:
    welcome:<msg>\n
    start_quiz\n
    question:<question_text>|<opt1>|<opt2>|... \n
    feedback:<text>\n
    leaderboard:user1:pts1|user2:pts2|...\n
    quiz_over:<text>\n
"""

import socket
import threading
import time
import select

HOST = "127.0.0.1"   # set to 0.0.0.0 to listen on all interfaces
PORT = 8888
DELIM = "\n"
QUESTION_TIME = 20  # seconds per question
POINTS = 10

clients = {}   # username -> socket
scores = {}    # username -> int
lock = threading.Lock()
quiz_started = False

# Example questions; you can load from file instead
questions = [
    {"q": "What is 2 + 2?", "options": ["2", "3", "4", "5"], "a": "4"},
    {"q": "Capital of France?", "options": ["Paris", "London", "Berlin", "Rome"], "a": "Paris"},
    {"q": "Python is a ____ language?", "options": ["Snake", "Programming", "Car", "Fruit"], "a": "Programming"},
]


def broadcast_line(text):
    """Send text + DELIM to all connected clients, removing dead sockets."""
    to_remove = []
    with lock:
        for user, conn in list(clients.items()):
            try:
                conn.sendall((text + DELIM).encode())
            except Exception:
                to_remove.append(user)
        for u in to_remove:
            print(f"🧹 Removing disconnected client: {u}")
            try:
                clients[u].close()
            except:
                pass
            clients.pop(u, None)
            scores.pop(u, None)


def accept_clients(server_sock):
    """Accept clients and register username from initial 'join:username' message."""
    while True:
        try:
            conn, addr = server_sock.accept()
            conn.setblocking(True)
            # short initial recv to capture join message
            try:
                conn.settimeout(5.0)
                raw = conn.recv(4096).decode()
                conn.settimeout(None)
                if not raw:
                    conn.close()
                    continue
                line = raw.split(DELIM)[0].strip()
                if line.startswith("join:"):
                    username = line.split(":", 1)[1].strip()
                    with lock:
                        if username in clients:
                            try:
                                clients[username].close()
                            except:
                                pass
                        clients[username] = conn
                        scores.setdefault(username, 0)
                    print(f"👤 {username} connected from {addr}")
                    # send welcome
                    try:
                        conn.sendall((f"welcome:Connected as {username}" + DELIM).encode())
                    except:
                        pass
                else:
                    try:
                        conn.sendall((f"error:expected join:<username>" + DELIM).encode())
                    except:
                        pass
                    conn.close()
            except Exception as e:
                print("⚠ Error receiving join message:", e)
                try:
                    conn.close()
                except:
                    pass
        except Exception as e:
            print("⚠ Error accepting client:", e)
            time.sleep(0.5)


def quiz_loop():
    """Centralized quiz loop that broadcasts questions and collects answers with select."""
    global quiz_started
    print("🚀 Quiz loop starting.")
    quiz_started = True
    broadcast_line("start_quiz")

    for q in questions:
        q_text = q["q"]
        opts = q["options"]
        correct = q["a"]

        q_msg = f"question:{q_text}|{'|'.join(opts)}"
        broadcast_line(q_msg)
        print("📤 Broadcasted question:", q_msg)

        deadline = time.time() + QUESTION_TIME
        first_correct = None

        while time.time() < deadline and first_correct is None:
            with lock:
                sockets = list(clients.values())
            if not sockets:
                print("⚠ No clients connected; waiting a bit...")
                time.sleep(0.5)
                continue

            timeout = max(0, deadline - time.time())
            try:
                readable, _, _ = select.select(sockets, [], [], timeout)
            except Exception as e:
                print("⚠ select error:", e)
                break

            for s in readable:
                try:
                    data = s.recv(4096).decode()
                    if not data:
                        # socket closed by client -> remove
                        uname = None
                        with lock:
                            for u, c in list(clients.items()):
                                if c is s:
                                    uname = u
                                    break
                            if uname:
                                print(f"🧹 Client {uname} closed connection.")
                                try:
                                    clients[uname].close()
                                except:
                                    pass
                                clients.pop(uname, None)
                                scores.pop(uname, None)
                        continue
                    # may contain multiple messages
                    for line in data.split(DELIM):
                        if not line:
                            continue
                        if line.startswith("answer:"):
                            ans = line.split(":", 1)[1].strip()
                            username = None
                            with lock:
                                for u, c in clients.items():
                                    if c is s:
                                        username = u
                                        break
                            if username is None:
                                continue
                            print(f"📨 Received answer from {username}: {ans}")
                            if ans == correct and first_correct is None:
                                first_correct = username
                                with lock:
                                    scores[username] = scores.get(username, 0) + POINTS
                                break
                except Exception as e:
                    print("⚠ Error reading socket:", e)
                    # remove socket
                    uname = None
                    with lock:
                        for u, c in list(clients.items()):
                            if c is s:
                                uname = u
                                break
                        if uname:
                            try:
                                clients[uname].close()
                            except:
                                pass
                            clients.pop(uname, None)
                            scores.pop(uname, None)

        if first_correct:
            broadcast_line(f"feedback:{first_correct} answered first and got it right!")
            print(f"🏆 First correct: {first_correct}")
        else:
            broadcast_line(f"feedback:No correct answers. Correct was: {correct}")
            print("⏱ No correct answers for:", q_text)

        # build leaderboard
        with lock:
            lb_parts = [f"{u}:{scores.get(u,0)}" for u in scores]
        broadcast_line("leaderboard:" + ("|".join(lb_parts) if lb_parts else ""))
        print("📊 Broadcasted leaderboard:", lb_parts)

        time.sleep(1)

    broadcast_line("quiz_over:Thanks for playing!")
    print("🏁 Quiz finished.")
    quiz_started = False


def host_control():
    """Host console loop: start, players, scores, quit."""
    global quiz_started
    while True:
        try:
            cmd = input("Command (start/players/scores/quit): ").strip().lower()
        except EOFError:
            cmd = "quit"
        if cmd == "start":
            if not quiz_started:
                t = threading.Thread(target=quiz_loop, daemon=True)
                t.start()
                print("🚀 Quiz started (thread).")
            else:
                print("⚠ Quiz already running.")
        elif cmd == "players":
            with lock:
                print("👥 Players:", list(clients.keys()))
        elif cmd == "scores":
            with lock:
                print("🏆 Scores:", scores)
        elif cmd in ("quit", "exit"):
            print("🛑 Exiting server (note: connected sockets may remain).")
            break
        else:
            print("❌ Unknown command.")


if __name__ == "__main__":
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"🎮 TCP Server running on {HOST}:{PORT}")

    threading.Thread(target=accept_clients, args=(server,), daemon=True).start()
    host_control()
    try:
        server.close()
    except:
        pass
