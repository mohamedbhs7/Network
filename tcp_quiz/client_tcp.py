# client_test.py
import socket

SERVER_IP = "192.168.54.220"  # your server IP
PORT = 8888

username = input("Enter your username: ")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((SERVER_IP, PORT))
    s.sendall(f"join:{username}".encode())
    print("Connected to server!")

    while True:
        data = s.recv(1024).decode()
        if data.startswith("question:"):
            q = data.replace("question:", "")
            print(f"Question: {q}")
            ans = input("Your answer: ")
            s.sendall(ans.encode())
        elif data.startswith("score:"):
            score = data.replace("score:", "")
            print(f"Score: {score}")
