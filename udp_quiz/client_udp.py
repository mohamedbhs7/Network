# client_udp.py
import socket
import threading
import sys

SERVER_IP = "127.0.0.1"  # or the LAN IP of the server
PORT = 8888

def listen_for_messages(sock):
    """Background thread to receive messages from server."""
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            msg = data.decode().strip()
            if msg.startswith("question:"):
                parts = msg.split(":")
                qid, text, opts = parts[1], parts[2], parts[3]
                print(f"\n📢 Question {qid}: {text}")
                print("Type your answer (a, b, c, etc.) and press Enter.")
            elif msg.startswith("broadcast:"):
                print("📣", msg.split(":", 1)[1])
            elif msg.startswith("score:"):
                _, user, points = msg.split(":")
                print(f"🏅 {user}: {points} points")
            else:
                print(msg)
        except:
            break

username = input("Enter your username: ")
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(f"join:{username}".encode(), (SERVER_IP, PORT))

# Start listening thread
threading.Thread(target=listen_for_messages, args=(sock,), daemon=True).start()

while True:
    msg = input("")  # allow user to type answer
    if msg.lower() in ["a", "b", "c", "d"]:
        sock.sendto(f"answer:{msg}".encode(), (SERVER_IP, PORT))
    elif msg.lower() == "quit":
        print("Leaving the game...")
        break
