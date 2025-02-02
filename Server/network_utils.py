import socket
import pickle

class NetworkUtils:
    def __init__(self, local_ip, buffer_size=1024):
        self.local_ip = local_ip
        self.buffer_size = buffer_size

    def send_Message(self, ip, message, port=5000):
        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPServerSocket.sendto(message, (ip, port))
        UDPServerSocket.close()

    def broadcast(self, ip, port, broadcast_message):
        # Create a UDP socket
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) #changed_remove
        # Send message on broadcast address
        broadcast_socket.sendto(broadcast_message.encode(), (ip, port))
        broadcast_socket.close()
        
    # get the messaged passed from clients ( have a message queue )
    def read_client(self, port, chatroom_timeout =False,heartbeat_leader=False, heatbeat_server=False):
            try:
                UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                # UDPServerSocket.setblocking(0)
                if heartbeat_leader:
                    UDPServerSocket.settimeout(5)
                if heatbeat_server:
                    UDPServerSocket.settimeout(45)
                if chatroom_timeout:
                    UDPServerSocket.settimeout(40)
                UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                #UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

                UDPServerSocket.bind((self.local_ip, port))
                # keep listening and get the message from clinet
                bytesAddressPair = UDPServerSocket.recvfrom(self.buffer_size)

                message = bytesAddressPair[0]

                address = bytesAddressPair[1]

                clientMsg = "Message from {} : {}".format(address, port)
                #clientIP = "Client IP Address:{}".format(address)

                print(clientMsg)
                #print(clientIP)

                UDPServerSocket.close()

                return [address, message]
            except socket.timeout:
                return False
            except Exception as e:
                print('Recving error: ', e)

    def write_to_client(self, server_message, client_ip, client_port):
        # Sending a reply to client
        # UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # UDPServerSocket.bind((client_ip, client_port))
        bytesToSend = str.encode(server_message)

        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPServerSocket.sendto(bytesToSend, (client_ip, client_port))
        print("sent {} to {} {}".format(bytesToSend, client_ip, client_port))
        UDPServerSocket.close()
        return True
        # pass

    