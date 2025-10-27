# client_udp_test.py
import socket

SERVER_IP = "192.168.54.63"  # use LAN IP if testing between PCs
PORT = 8888

# Create a UDP socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    message = b"Hello from UDP client!"
    s.sendto(message, (SERVER_IP, PORT))  # send one datagram
    print("Message sent to server.")

    data, addr = s.recvfrom(1024)  # wait for reply (up to 1024 bytes)
    print("Server says:", data.decode())
