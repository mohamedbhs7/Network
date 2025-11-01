# server_udp_test.py
import socket
import threading
import json
import time
import queue

questions = []

with open('questions.json') as file:
    questions = json.load(file)["questions"]

HOST = "127.0.0.1"   # or "0.0.0.0" to listen on all network interfaces
PORT = 8888
TIME = 30  # seconds
POINTS = 10

clients = {}
scores = {}

message_queue = queue.Queue()

# Send a message to all connected clients.
def broadcast(server, message):
    for addr in clients:
        server.sendto(message.encode(), addr)

# Main quiz loop once started by operator.
def quiz_game(server):
    print("\n✅ Quiz starting now!")
    broadcast(server, "broadcast:The quiz is starting now!\n")

    for q in questions:
        question_msg = f"question {q['id']}: {q['question']}\n{q['options']}"
        broadcast(server, question_msg)
        print(f"\n📨 Sent: {q['question']}")

        start_time = time.time()
        answered = False

        while time.time() - start_time < TIME:
            server.settimeout(1)
            try:
                addr, msg = message_queue.get(timeout=1)
                if msg.startswith("answer:"):
                    answer = msg.split(":")[1]
                    user = clients.get(addr, "Unknown")
                    if answer == q["correct_answer"] and not answered:
                        scores[user] += POINTS
                        broadcast(server, f"broadcast:{user} answered correctly and got {POINTS} points!")
                        answered = True
                        break
            except queue.Empty:
                continue
            except socket.timeout:
                continue

        if not answered:
            broadcast(server, f"broadcast:Time’s up! Correct answer was {q['correct_answer']}.")

        # Send scores
        for u, s in scores.items():
            broadcast(server, f"score:{u}:{s}")
        time.sleep(2)

    broadcast(server, "broadcast:Game over! Thanks for playing.")
    print("\n🏁 Game finished.")


# Server setup
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
    server.bind((HOST, PORT))
    print(f"🎮 UDP Server listening on {HOST}:{PORT}")

    # Run listener in a separate thread to allow manual quiz start
    def listen_for_clients():
        while True:
            try:
                data, addr = server.recvfrom(1024)
                msg = data.decode().strip()
                message_queue.put((addr, msg))
                if msg.startswith("join:"):
                    username = msg.split(":", 1)[1]
                    if len(username) == 0:
                        username = f"Guest {len(clients) + 1}" 
                    clients[addr] = username
                    scores[username] = 0
                    print(f"👤 {username} joined from {addr}")
                    server.sendto(f"Welcome {username}! Waiting for quiz to start...".encode(), addr)

            except socket.timeout:
                continue

    listener_thread = threading.Thread(target=listen_for_clients, daemon=True)
    listener_thread.start()

    input("\n🕹️ Press ENTER to start the quiz once all players have joined...")
    quiz_game(server)