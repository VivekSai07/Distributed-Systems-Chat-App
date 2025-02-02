import socket
import threading

class ListernToLeader:
    def __init__(self, local_ip, buffer_size=1024):
        self.local_ip = local_ip
        self.buffer_size = buffer_size
        self.server_ip = None

    def keep_listening_to_leader(self, output_input):
        """
        Listens for updates from the leader (server) and updates the server IP.
        """
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to a specific port for leader updates
            port = 10002 if output_input else 10003
            client_socket.bind((self.local_ip, port))
            # print(f"Listening for leader updates on port {port}...")
            while True:
                data, server = client_socket.recvfrom(self.buffer_size)
                new_server_ip = data.decode()
                print(f"🌐 **NEW SERVER IP FOR CHATROOM**: {new_server_ip}")
                self.server_ip = new_server_ip
        except Exception as e:
            print(f"⚠️ **Error in keep_listening_to_leader**: {e}")
        finally:
            client_socket.close()

    def start_listening(self, output_input):
        """
        Starts a thread to listen for leader updates.
        """
        leader_thread = threading.Thread(target=self.keep_listening_to_leader, args=(output_input,))
        # leader_thread.daemon = True  # Daemonize thread to exit when the main program exits
        leader_thread.start()