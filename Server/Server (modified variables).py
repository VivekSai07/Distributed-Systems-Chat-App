import socket
import json
import time
import select
import pickle
import multiprocessing
from multiprocessing.pool import ThreadPool
import threading
from dynamic_ip import get_local_ip_and_broadcast
import uuid
from threading import *

MY_HOSTNAME = socket.gethostname()
localIP, BROADCAST_ADDR     = get_local_ip_and_broadcast()
localPort   = 10001      
bufferSize  = 1024
process_queue = multiprocessing.Queue(maxsize = 100)
leader_ip = localIP
localPort_in   = 5002    
localPort_out = 5003     
local_server_port = 4444 

class CustomThread(Thread):
    def __init__(self, localPort_out):
        Thread.__init__(self)
        self.value = None
        self.localPort_out = localPort_out

    def run(self):
        serve2 = Server()
        self.value = serve2.readClient(self.localPort_out, True,False, False)

class Server():
    my_uid = str(uuid.uuid1())
    chatrooms_handled = []
    group_view = [] 
    ACKCounter = {}
    server_list = []
    client_list = []
    hbList = {}
    ip_address = localIP
    is_leader = False
    leader_for_first_time = True
    leader_id = ""
    server_id = ""
    leader = ""

    def __init__(self):
        pass

    def BCListener(self, socket, role):
        print(f"[INFO] Listening for broadcast messages as {role}...")
        print(localIP)
        while True:
            data, server = socket.recvfrom(1024)
            if data:
                return data

    ########## Functions for Dynamic Discovery ##########
    # These functions facilitate the dynamic identification and exploration of relevant elements
    def sendMsg(self, ip, message):
        ServerSocket_UDP = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        ServerSocket_UDP.sendto(message, (ip,5000))
        ServerSocket_UDP.close()

    def acptLogin(self, server):
        
        while True:
            try:
                if self.is_leader == False:
                    ServerSocket_UDP = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                    return
                ServerSocket_UDP = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                ServerSocket_UDP.bind((localIP, localPort))
                ServerSocket_UDP.settimeout(10)
                data = self.BCListener(ServerSocket_UDP,'client')
                ServerSocket_UDP.close()
                userInformation = data.decode().split(',')
                print(userInformation)
                newUser = {'IP' : userInformation[0], 'userName' : userInformation[1], "chatID": 0}
                print("Send groupview to " + newUser['IP'])
                new_group_view_without_leader = []
                for server in self.group_view:
                    if server['IP'] != self.ip_address:
                        new_group_view_without_leader.append(server)
                      
                send_group_view_to_client = pickle.dumps(new_group_view_without_leader)
                self.sendMsg(newUser['IP'], send_group_view_to_client)
                ServerSocket_UDP = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                ServerSocket_UDP.bind((localIP, localPort))  # changed_remove
                ServerSocket_UDP.settimeout(10)
                print("Waiting for client responses to join the chatroom...")
                data = self.BCListener(ServerSocket_UDP, 'client')
                ServerSocket_UDP.close()
                userSelection = pickle.loads(data)
                selected_server_id = userSelection['selected_server']
                selected_charoom = userSelection['selected_chatroom']
                for server in self.group_view:
                    if server['serverID'] == int(selected_server_id):
                        for chatrooms in server['chatrooms_handled']:
                            if chatrooms['inPorts'][0] == selected_charoom:
                                new_chatroom_clients = []
                                for clients in chatrooms['clients_handled']:
                                    new_chatroom_clients.append(clients)
                                new_chatroom_clients.append(json.dumps(userSelection))
                                chatrooms['clients_handled'] = set(new_chatroom_clients)
                message = pickle.dumps(self.group_view)
                self.send_to_all_servers(server, message, 5044)  
                time.sleep(1)
                self.sendMsg(userSelection['IP'], b"Kindly connect to the assigned server and join the designated chatroom.")
                if self.is_leader == False:
                    return
            except socket.timeout:
                ServerSocket_UDP.close()
                self.acptLogin(server)
            except UnicodeDecodeError:
                ServerSocket_UDP.close()
                self.acptLogin(server)
            except pickle.UnpicklingError:
                ServerSocket_UDP.close()
                self.acptLogin(server)
            finally:
                ServerSocket_UDP.close()

    def broadcast_message(self, ip, port, broadcast_message):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.sendto(broadcast_message.encode(), (ip, port))
        broadcast_socket.close()

    def convert_sets(self, obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self.convert_sets(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_sets(i) for i in obj]
        return obj

    def joinNwk(self, server):
        self.broadcast_message(BROADCAST_ADDR, 5043, self.ip_address)
        LeaderSS = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        LeaderSS.bind((localIP, 5044))
        LeaderSS.setblocking(0)
        ready = select.select([LeaderSS],[],[], 3)
        if ready[0]:
            data, server = LeaderSS.recvfrom(4096)
            LeaderSS.close()
            self.group_view = pickle.loads(data)
            self.group_view = self.convert_sets(self.group_view)
            print("All Connected Server Data:\n" + json.dumps(self.group_view, indent=4))
            self.leader = server[0]
            for server in self.group_view:
                if server['IP'] == self.ip_address:
                    self.server_id = server['serverID']
                if server['IP'] == self.leader:
                    self.leader_id = server['serverID']
            self.strtElection(server)
        else:
            print(f"🚀 Leadership acquired! I am the new leader (IP: {self.ip_address}).")
            self.leader = self.ip_address
            self.is_leader = True
            self.group_view.append({"serverID": 0, "IP" : self.ip_address, "chatrooms_handled" : [{"inPorts": [6000], "outPorts": [6001], 'clients_handled':[]}],'heartbeat_port':4444})
            self.server_id = 0
            self.leader_id = 0
        LeaderSS.close()

    def calculate_ports(self):
        current_ports = []
        for server in self.group_view:
            for chatrooms in server['chatrooms_handled']:
                current_ports.append(chatrooms['inPorts'][0])
                current_ports.append(chatrooms['outPorts'][0])
        if len(current_ports) == 0:
            new_inport = 5000
            new_outport = 5001
        else:
            current_ports.sort()
            new_inport = max(current_ports) + 1
            new_outport = new_inport + 1
        return [new_inport],[new_outport]


    def acptJoin(self, server):
        while True:
            if self.is_leader == False:
                    return
            try:
                LeaderSS = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                LeaderSS.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                LeaderSS.settimeout(4)
                LeaderSS.bind((localIP, 5043))
                newServerIP = self.BCListener(LeaderSS,'server')
                LeaderSS.close()
                print(self.group_view)
                newServerID = max(self.group_view, key = lambda x:x['serverID'])['serverID'] + 1
                inports, outports = self.calculate_ports()
                newServer = {"serverID": newServerID, "IP" : newServerIP.decode(),"chatrooms_handled" : [{"inPorts": inports, "outPorts": outports, 'clients_handled':[]}],'heartbeat_port':4444}
                self.group_view.append(newServer)
                self.hbList[newServerIP.decode()] = 0  
                message = pickle.dumps(self.group_view)
                print(message)
                self.send_to_all_servers(server, message, 5044)
                LeaderSS.close()
            except socket.timeout:
                LeaderSS.close()
                if self.is_leader:
                    self.acptJoin(server)


    def send_to_clients_new_server(self,chatroom,new_server_ip):
        for clients in chatroom['clients_handled']:
            cur_client = json.loads(clients)
            client_ip = cur_client['IP']
            client_out_port = 10002
            client_in_port = 10003
            ServerSocket_UDP = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            ServerSocket_UDP.sendto(new_server_ip.encode(), (client_ip, client_in_port))
            ServerSocket_UDP.sendto(new_server_ip.encode(), (client_ip, client_out_port))
            ServerSocket_UDP.close()

    def send_to_all_servers(self, server, message, port):
        LeaderSS = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        for i in self.group_view:
            LeaderSS.sendto(message, (i['IP'],port))
        LeaderSS.close()

    def updateGrpView(self, server):
        try:
            LeaderSS = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            LeaderSS.bind((localIP, 5044))
            LeaderSS.settimeout(5)
            data, server = LeaderSS.recvfrom(4096)
            LeaderSS.close()
            self.group_view = pickle.loads(data)
            print("Updated Groupview: " + json.dumps(self.convert_sets(self.group_view), indent=4))
            if self.is_leader == False:
                self.updateGrpView(server)
        except socket.timeout:
            LeaderSS.close()
            if self.is_leader == False:
                self.updateGrpView(server)

    def updateClientList(self, server):
        try:
            clientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            clientSocket.bind((localIP, 5045))
            clientSocket.settimeout(5)
            data, server = clientSocket.recvfrom(4096)
            clientSocket.close()
            self.client_list = pickle.loads(data)
            print("New Clientlist: " + str(self.client_list))
            if self.is_leader == False:
                self.updateClientList(server)
        except socket.timeout:
            clientSocket.close()
            if self.is_leader == False:
                self.updateClientList(server)    
    
    ########## Functions for Leader Election ##########
    def strtElection(self, server):
        print("My UID: ", self.my_uid)
        self.updateSList(server)
        if len(self.server_list) == 1:
                self.leader = self.ip_address
                self.is_leader = True
                print(f"🚀 Leadership acquired! I am the new leader (IP: {self.ip_address}).")
                return
        ring = self.ring_formation(self.server_list)
        neighbour = self.fetch_neighbour(ring, self.ip_address,'left')
        ringSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ringSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        message = pickle.dumps({"mid": self.my_uid, "isLeader": False, "IP": self.ip_address})
        print("Started election, send message ", pickle.loads(message), "to ", neighbour)
        ringSocket.sendto(message,(neighbour,5892))
        ringSocket.close()

    def election(self, server):
        participant = False
        while True:
            ringSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ringSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
            ringSocket.bind((self.ip_address, 5892))
            self.updateSList(server)
            ring = self.ring_formation(self.server_list)
            neighbour = self.fetch_neighbour(ring, self.ip_address,'left')
            print("⚡Listening for incoming election messages...")
            data, adress = ringSocket.recvfrom(bufferSize)
            self.updateSList(server)
            time.sleep(1)
            ring = self.ring_formation(self.server_list)
            neighbour = self.fetch_neighbour(ring, self.ip_address,'left')
            election_message = pickle.loads(data)
            print("Election message:", election_message)
            if election_message['isLeader'] and not election_message['mid'] == self.my_uid:
                self.leader = election_message['IP']
                print(f"🎉 The elected Leader is: {self.leader} 👑")
                participant = False
                print("Send election Message(case1) ", election_message, " to ", neighbour, " at ", time.time())
                ringSocket.sendto(data,(neighbour,5892))
                self.is_leader = False
                
            if election_message['isLeader'] and  election_message['mid'] == self.my_uid:
                print("Election finished, Leader is ", self.leader)
                continue

            if election_message['mid'] < self.my_uid and not participant:
                new_election_message = {
                    "mid": self.my_uid, 
                    "isLeader": False,
                    "IP": self.ip_address
                }
                participant = True
                ringSocket.sendto(pickle.dumps(new_election_message),(neighbour,5892))
                print("Send election Message(case 3) ", new_election_message, " to ", neighbour, " at ", time.time())

            elif election_message['mid'] > self.my_uid:
                participant = True
                ringSocket.sendto(data,(neighbour,5892))
                print("Send election Message(case4) ", election_message, " to ", neighbour, " at ", time.time() )

            elif election_message['mid'] == self.my_uid and not election_message['isLeader']:
                self.leader = self.ip_address
                self.is_leader = True
                new_election_message = {
                    "mid": self.my_uid,
                    "isLeader": True,
                    "IP": self.ip_address
                }
                ringSocket.sendto(pickle.dumps(new_election_message),(neighbour,5892))
                print("Send election Message(case5) ", new_election_message, " to ", neighbour, " at ", time.time())
                print(f"🚀 Leadership acquired! I am the new leader (IP: {self.ip_address}).")
                participant = False
                ringSocket.close()

    def updateSList(self, server):
        self.server_list = []
        for i in self.group_view:
            self.server_list.append(i['IP'])
        self.server_list = list(dict.fromkeys(self.server_list))

    def ring_formation(self, member_list):
        sorted_binary_ring = sorted([socket.inet_aton(member) for member in member_list])
        sorted_ip_ring = [socket.inet_ntoa(node) for node in sorted_binary_ring]
        return sorted_ip_ring
    
    def fetch_neighbour(self, ring, current_node_ip, direction = 'left'):
        current_node_index = ring.index(current_node_ip) if current_node_ip in ring else -1
        if current_node_ip != -1:
            if direction == 'left':
                if current_node_index +1 == len(ring):
                    return ring[0]
                else:
                    return ring[current_node_index + 1]
            else:
                if current_node_index == 0:
                    return ring[len(ring) - 1]
                else:
                    return ring[current_node_index -1]
        else:
            return None

    def receive_hb(self):
        print("\nMonitoring Leader's Heartbeat...")
        leader_heartbeat = self.readClient(4444,False,heartbeat_leader=False,heatbeat_server=True)  
        print("📩 LEADER_HEARTBEAT_RECEIVED: ",leader_heartbeat)
        if leader_heartbeat:
            if leader_heartbeat[1] == b'heartbeat':
                time.sleep(1)
                thread = threading.Thread(target=self.writeToClient, args=('HB_received', self.leader, local_server_port,))
                thread.start()
                thread.join()
        else:
            if self.is_leader:
                return True
            print('Leader is unresponsive, initiating election process...')
            print('Updating group view and triggering election procedure...')
            new_group_view = []
            dummy_server = None
            for server in self.group_view:
                if server['IP'] == self.leader:
                    pass
                else:
                    new_group_view.append(server)
            self.group_view = new_group_view
            new_group_view = pickle.dumps(new_group_view)
            self.send_to_all_servers(dummy_server,new_group_view,5044)
            self.strtElection(dummy_server)
            if self.is_leader:
                return True
            else:
                return False

    def send_heartbeat(self):
        for server in self.group_view:
            if self.is_leader == False:
                print('No longer the leader.')
                return True
            server_id = server['serverID']
            server_ip = server['IP']
            server_port = server['heartbeat_port']
            if self.leader_for_first_time:
                self.hbList[server_ip] = 0
                self.leader_for_first_time = False
            if server_ip != self.leader:
                thread = threading.Thread(target=self.writeToClient,args=("heartbeat",server_ip,server_port,))
                thread.start()
                pool = ThreadPool(processes=1)
                async_result = pool.apply_async(self.readClient, (local_server_port,False,True,False)) 
                listen_heartbeat = async_result.get()
                print(self.hbList)
                if self.is_leader == False: 
                    return True
                if listen_heartbeat:
                    if listen_heartbeat[1] == b'HB_received':
                        print("\nServer {} is alive:".format(listen_heartbeat[0][0]))
                        self.hbList[listen_heartbeat[0][0]] = 0     
                else:
                    if self.hbList[server_ip] > 3:   
                        print("\nServer {} {} is dead:".format(server_ip,server_id))
                        self.hbList[server_ip] = 0  
                        new_group_view = []
                        new_client_list = None
                        dummy_server = None
                        for server in self.group_view:
                            if server['IP'] == server_ip:
                                new_chatroom = server['chatrooms_handled']
                                pass
                            else:
                                new_group_view.append(server)
                        self.group_view = new_group_view
                        min_cli = 10000
                        clients_transfered = False
                        for servers in self.group_view:
                            for chatrooms in servers['chatrooms_handled']:
                                min_cli = min(len(chatrooms['clients_handled']),min_cli)
                        for servers in self.group_view:
                            if clients_transfered == True:
                                continue
                            for chatrooms in servers['chatrooms_handled']:
                                if len(chatrooms['clients_handled']) == min_cli:
                                    servers['chatrooms_handled'].append(new_chatroom[0])  
                                    new_server_ip = servers['IP']
                                    clients_transfered = True
                                    continue
                                else:
                                    min_cli = min(len(chatrooms['clients_handled']),min_cli)
                        print("\n--- New Client List After Server Down ---")
                        print(new_client_list)
                        print("\n--- New Group View After Server Down ---")
                        print(json.dumps(self.convert_sets(self.group_view), indent=4))
                        new_group_view = pickle.dumps(self.group_view)
                        self.send_to_all_servers(dummy_server, new_group_view, 5044)
                        self.send_to_clients_new_server(new_chatroom[0],new_server_ip)
                    self.hbList[server_ip] = self.hbList[server_ip] + 1   

    def hbMechanism(self):
        while True:  
            if self.is_leader:
                is_leader = self.send_heartbeat()  
                if is_leader:
                    print("🚫 \033[1;31mNot the leader anymore...\033[0m 😞")
                    return True
            else:
                is_leader = self.receive_hb()
                for server in self.group_view:
                    self.hbList[server['IP']] = 0
                if is_leader:
                    return

    def readClient(self, port, chatroom_timeout =False,heartbeat_leader=False, heatbeat_server=False):
            try:
                ServerSocket_UDP = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                if heartbeat_leader:
                    ServerSocket_UDP.settimeout(5)
                if heatbeat_server:
                    ServerSocket_UDP.settimeout(45)
                if chatroom_timeout:
                    ServerSocket_UDP.settimeout(40)
                ServerSocket_UDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                ServerSocket_UDP.bind((localIP, port))
                bytesAddressPair = ServerSocket_UDP.recvfrom(bufferSize)
                message = bytesAddressPair[0]
                address = bytesAddressPair[1]
                clientMsg = "Incoming message from {} → {}".format(address, port)
                print(clientMsg)
                ServerSocket_UDP.close()
                return [address, message]
            except socket.timeout:
                return False
            except Exception as e:
                print('Recving error: ', e)

    def writeToClient(self, server_message, client_ip, client_port):
        bytesToSend = str.encode(server_message)
        ServerSocket_UDP = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        ServerSocket_UDP.sendto(bytesToSend, (client_ip, client_port))
        print("📤 Acknowledgment sent: {} → {}:{}".format(bytesToSend, client_ip, client_port))
        ServerSocket_UDP.close()
        return True

    def writeToClient_with_ack(self, server_message, client_ip, client_port, from_client_ip,chatroom_inport,chatroom_outport):
        bytesToSend = str.encode(server_message)
        ServerSocket_UDP = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        ServerSocket_UDP.sendto(bytesToSend, (client_ip, client_port))
        print("📤 Acknowledgment sent: {} → {}:{}".format(bytesToSend, client_ip, client_port))
        ServerSocket_UDP.close()
        thread = CustomThread(chatroom_outport)
        thread.start()
        thread.join()
        ack_thread = thread.value
        if ack_thread:
            ackkkk = ack_thread[1].split(b'-')
            if ackkkk[1] == b'recvd':
                self.ACKCounter[from_client_ip][chatroom_inport] = self.ACKCounter[from_client_ip][chatroom_inport] + 1
        else:
            pass
        return True

    def parse_client_message(self, client_recv_data):
        data_list = client_recv_data.split("-")
        client_id = data_list[0]
        client_req = data_list[1]
        chatroom_id = data_list[2]
        client_message = data_list[3]
        vc = data_list[4]
        userName = data_list[5]
        client_port_out = data_list[-2]
        client_port = data_list[-1]
        return [client_message,vc,userName, client_port]

    def collectChatroom(self):
        try:
            while True:
                for servers in self.group_view:
                    if servers['IP'] == self.ip_address: 
                        self.chatrooms_handled = servers['chatrooms_handled']
                        for chatrooms in self.chatrooms_handled:
                            if len(chatrooms['clients_handled']) == 0:
                                continue
                            current_chatroom = chatrooms
                            clients_for_this_room = chatrooms['clients_handled']
                            chatroom_inport = current_chatroom['inPorts'][0]
                            chatroom_outport = current_chatroom['outPorts'][0]
                            p_room = threading.Thread(target=self.collectClients,args=(chatrooms,chatroom_inport,chatroom_outport))
                            p_room.start()
                        for chatrooms in self.chatrooms_handled:
                            if len(chatrooms['clients_handled']) == 0:
                                continue
                            p_room.join()
        except AttributeError as e:
                print("ATTR ERROR: ",e)

    def collectClients(self,chatrooms,chatroom_inport,chatroom_outport):
        for chatroom in self.chatrooms_handled:
            if len(chatroom['clients_handled']) == 0:
                continue
            for client in chatroom['clients_handled']:
                p_chat = threading.Thread(target=self.writeToChatroom, args=(chatrooms,chatroom_inport,chatroom_outport,))
                p_chat.start()
        for chatroom in self.chatrooms_handled:
            if len(chatroom['clients_handled']) == 0:
                continue
            for client in chatroom['clients_handled']:
                p_chat.join()

    def writeToChatroom(self,chatrooms,chatroom_inport,chatroom_outport):
        while True:
            bytesAddressPair = self.readClient(chatroom_inport,True)  
            if bytesAddressPair == False:
                return
            print("Now in chatroom : ",chatroom_inport)
            message_parts = bytesAddressPair[1].decode().split("-")
            message_to_send = message_parts[3]
            user_name = message_parts[5]
            print(f"💬 New message in chatroom {chatroom_inport} 📲 from {bytesAddressPair[0]} (User:{user_name}) : {message_to_send} 📝")
            # print(f"💬 New message in chatroom {chatroom_inport} 📲 from {bytesAddressPair[0]}: {bytesAddressPair[1].decode()} 📝")
            message_from_client = bytesAddressPair[1].decode('utf-8')
            from_client_ip = bytesAddressPair[0][0]
            message, vc,userName, from_inport = self.parse_client_message(
                message_from_client)
            self.ACKCounter[from_client_ip] = {}
            self.ACKCounter[from_client_ip][chatroom_inport] = 0
            print("ACKcount_b2", self.ACKCounter[from_client_ip][chatroom_inport])
            for chatroom in self.chatrooms_handled:
                if int(chatroom['inPorts'][0]) == int(chatroom_inport):
                    number_of_clients = len(chatroom['clients_handled'])
                    for clients in chatroom['clients_handled']:
                        actual_client = json.loads(clients)
                        to_client_ip = actual_client['IP']
                        to_client_port = actual_client['outPorts']
                        thread = threading.Thread(target=self.writeToClient_with_ack,
                                                args=(message+"-"+vc+"-"+from_client_ip+"-"+userName, to_client_ip, to_client_port, from_client_ip,chatroom_inport,chatroom_outport,))
                        thread.start()
                        thread.join()
            print("ACKcount_a", self.ACKCounter[from_client_ip][chatroom_inport])
            if self.ACKCounter[from_client_ip][chatroom_inport] == number_of_clients:
                thread = threading.Thread(target=self.writeToClient,
                                          args=("sent", from_client_ip, int(from_inport),))
                thread.start()
                thread.join()
            else:
                thread = threading.Thread(target=self.writeToClient,
                                          args=("resend", from_client_ip, int(from_inport),))
                thread.start()
                thread.join()

def heartbeats():
    while True:
        if s.is_leader == True:
            pool1 = ThreadPool(processes=1)
            async_result = pool1.apply_async(s.hbMechanism, ())  
            listen_heartbeat = async_result.get()
            if listen_heartbeat:
                return
        else:
            pool2 = ThreadPool(processes=1)
            async_result = pool2.apply_async(s.hbMechanism, ())  
            listen_heartbeat = async_result.get()
            if listen_heartbeat:
                return

if __name__ == "__main__":
    s = Server()
    s.joinNwk(s)
    p_chat = threading.Thread(target=s.collectChatroom, args=())
    p_chat.start()
    p_election = threading.Thread(target = s.election, args = (s,))
    p_election.start()
    while True:
        if s.is_leader == True:
            p_join = threading.Thread(target = s.acptJoin, args = (s,))
            p_join.start()
            p_login = threading.Thread(target = s.acptLogin, args = (s,))
            p_login.start()
            p_heart = threading.Thread(target=heartbeats, args=())
            p_heart.start()
            p_login.join()
            p_join.join()
        else:
            p_groupviewUpdate = threading.Thread(target = s.updateGrpView, args = (s,))
            p_groupviewUpdate.start()
            p_clientUpdate = threading.Thread(target = s.updateClientList, args = (s,))
            p_clientUpdate.start()
            p_election = threading.Thread(target = s.election, args = (s,))
            p_election.start()
            p_heart = threading.Thread(target= heartbeats, args=())
            p_heart.start()
            p_groupviewUpdate.join()
            p_clientUpdate.join()