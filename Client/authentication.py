import socket
import pickle
import json

client_inport = 5566
client_outport = 5565
class Authentication:
    def __init__(self, local_ip, broadcast_ip, server_port, buffer_size=1024):
        self.local_ip = local_ip
        self.broadcast_ip = broadcast_ip
        self.server_port = server_port
        self.buffer_size = buffer_size

    def broadcast(self, ip, port, broadcast_message, broadcast_socket):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if type(broadcast_message) == str:
            broadcast_socket.sendto(str.encode(broadcast_message), (ip, port))
        else:
            broadcast_socket.sendto(broadcast_message, (ip, port))
        broadcast_socket.close()
        
    def convert_sets(self, obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self.convert_sets(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_sets(i) for i in obj]
        return obj
    
    def login(self, userName):
        try:
            message = self.local_ip + ',' + userName
            broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            if type(message) == str:
                broadcast_socket.sendto(str.encode(message), (self.broadcast_ip, self.server_port))
            else:
                broadcast_socket.sendto(message, (self.broadcast_ip, self.server_port))
            broadcast_socket.close()


            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client_socket.settimeout(12)
            client_socket.bind((self.local_ip, 5000))
            print('⏳ Awaiting response...')
            data, server = client_socket.recvfrom(self.buffer_size)
            client_socket.close()
            server_list = pickle.loads(data)
            server_list = self.convert_sets(server_list)
            if not server_list:
                print('⚠️ No servers are currently available, please hold on...')
                return self.login(userName)
            print('🔍 Choose a server ID and the corresponding chatroom ID (inport) to join a chatroom: \n', json.dumps(server_list, indent=4))
            selected_server = input("🌐 Please provide the server ID:  ")
            selected_chatroom = input("💬 Please enter the chatroom ID (inport):  ")
            for server in server_list:
                if int(selected_server) == server['serverID']:
                    for chatrooms in server['chatrooms_handled']:
                        if chatrooms['inPorts'][0] == int(selected_chatroom):
                            print("Configuring the chatroom")
                            inport = chatrooms['inPorts']
                            outport = chatrooms['outPorts']
                            server_ip = server['IP']

            print(f"🎉 Chatroom ready! 🌐 Ports: [IN] {inport[0]} ↔ [OUT] {outport[0]} 🖧")
            server_inport = inport[0]
            server_outport = outport[0]
            client = {'UserName': userName, 'IP': self.local_ip, "inPorts": client_inport , "outPorts": client_outport, "selected_server":selected_server, "selected_chatroom": server_inport}
            client_object = pickle.dumps(client)
            client_object = self.convert_sets(client_object)
            broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # changed_remove
            self.broadcast(self.broadcast_ip, self.server_port, client_object, broadcast_socket)  # changed_remove
            broadcast_socket.close()
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.bind((self.local_ip, 5000))
            client_socket.settimeout(3)
            print('⏳ Awaiting response... 🌐') 
            data, server = client_socket.recvfrom(self.buffer_size)
            client_socket.close()
            print(data)
            return server_ip, server_inport, server_outport
        except socket.timeout:
            client_socket.close()
            return self.login(userName)
        finally:
            client_socket.close()