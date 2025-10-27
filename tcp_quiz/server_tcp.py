import socket
import threading
import time

# ---------------------- Server Configuration ----------------------
HOST = "192.168.54.220"  # Server IP
PORT = 8888               # Port number

clients = {}              # Stores connected clients: {username: conn}
scores = {}               # Stores scores: {username: score}
quiz_started = False      # Flag to start quiz when host types "start"

# List of questions
questions = [
    {"q": "What is 2 + 2?", "options": ["2", "3", "4", "5"], "a": "4"},
    {"q": "Capital of France?", "options": ["Paris", "London", "Berlin", "Rome"], "a": "Paris"},
    {"q": "Python is a ____ language?", "options": ["Snake", "Programming", "Car", "Fruit"], "a": "Programming"},
]

lock = threading.Lock()  # Protect shared resources

# ---------------------- Broadcast to All Clients ----------------------
def broadcast(message):
    """Send a message to all connected clients safely."""
    with lock:
        disconnected = []
        for username, client in clients.items():
            try:
                client.sendall(message.encode())
            except:
                disconnected.append(username)  # Collect disconnected clients
        for username in disconnected:
            del clients[username]  # Remove disconnected clients

# ---------------------- Handle Each Client ----------------------
def handle_client(conn, username):
    """Manage a single client's session."""
    print(f"✅ {username} joined the game!")
    with lock:
        scores[username] = 0
        clients[username] = conn

    try:
        # Wait until host starts the quiz
        while not quiz_started:
            time.sleep(0.1)

        # Send all questions
        for q in questions:
            options_str = "|".join(q["options"])
            conn.sendall(f"question:{q['q']}|{options_str}".encode())

            print(f"❓ Question sent to {username}: {q['q']} Options: {q['options']}")

            try:
                answer = conn.recv(1024).decode().strip()
                correct = answer == q["a"]
                with lock:
                    if correct:
                        scores[username] += 1

                print(f"✉ {username} answered: {answer} | {'✅ Correct' if correct else '❌ Wrong'}")
                print(f"🏆 Updated Scores: {scores}")

                conn.sendall(f"score:{scores[username]}".encode())
            except:
                print(f"⚠ {username} disconnected mid-quiz")
                break

            time.sleep(0.5)

        # Notify client quiz is over
        conn.sendall("quiz_over:Thanks for playing!".encode())
        print(f"🏁 {username} finished the quiz!")

    except Exception as e:
        print(f"⚠ {username} disconnected: {e}")

    finally:
        conn.close()
        with lock:
            if username in clients:
                del clients[username]
            if username in scores:
                del scores[username]

# ---------------------- Accept New Clients ----------------------
def accept_clients(server):
    """Continuously accept incoming client connections."""
    while True:
        try:
            conn, addr = server.accept()
            data = conn.recv(1024).decode()
            if data.startswith("join:"):
                username = data.split(":")[1].strip()
                threading.Thread(target=handle_client, args=(conn, username), daemon=True).start()
        except Exception as e:
            print("⚠ Error accepting client:", e)

# ---------------------- Host Control ----------------------
def host_control():
    """Listen for host commands: start quiz, show players, show scores."""
    global quiz_started
    while True:
        cmd = input("").strip()
        if cmd.lower() == "start" and not quiz_started:
            print("🚀 Quiz Starting...")
            quiz_started = True
            broadcast("start_quiz")
        elif cmd.lower() == "players":
            with lock:
                print("👥 Connected Players:", list(clients.keys()))
        elif cmd.lower() == "scores":
            with lock:
                print("🏆 Scores:", scores)
        else:
            print("❌ Unknown command. Use 'start', 'players', or 'scores'.")

# ---------------------- Main Program ----------------------
if __name__ == "__main__":
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"🎮 Server is running on {HOST}:{PORT}")
    print("Type 'start' to launch quiz | 'players' to view players | 'scores' to view scores")

    # Start accepting clients in a separate daemon thread
    threading.Thread(target=accept_clients, args=(server,), daemon=True).start()
    host_control()  # Main thread handles host commands
