# server_udp_test.py
import socket

HOST = "192.168.100.128"   # or "0.0.0.0" to listen on all network interfaces
PORT = 8888
TIME = 30  # seconds
POINTS = 10

# Create a UDP socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
    server.bind((HOST, PORT))
    print(f"UDP Server listening on {HOST}:{PORT}")

    while True:
        data, addr = server.recvfrom(1024)  # No accept(), directly receives data
        print(f"Received from {addr}: {data.decode()}")
        server.sendto(b"Hello from UDP server!", addr)  # Reply to sender
