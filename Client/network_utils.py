import socket
import pickle

class NetworkUtils:
    def __init__(self, local_ip, buffer_size=1024):
        self.local_ip = local_ip
        self.buffer_size = buffer_size

    def send_message(self, s_address, s_port, message_to_b_sent):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.sendto(str.encode(message_to_b_sent), (s_address, s_port))
        finally:
            client_socket.close()

    def recieve_message(self, port, ackk=False):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client_socket.settimeout(40 if ackk else 5)
            client_socket.bind((self.local_ip, port))
            data, server = client_socket.recvfrom(self.buffer_size)
            return data
        except socket.timeout:
            return False
        finally:
            client_socket.close()

    def broadcast(self, ip, port, broadcast_message):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if type(broadcast_message) == str:
            broadcast_socket.sendto(str.encode(broadcast_message), (ip, port))
        else:
            broadcast_socket.sendto(broadcast_message, (ip, port))
        broadcast_socket.close()