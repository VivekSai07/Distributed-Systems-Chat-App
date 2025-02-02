import socket
import pickle
import time
import threading
from multiprocessing.pool import ThreadPool

bufferSize  = 1024
local_server_port = 4444   #heartbeat

class LeaderElection:
    def __init__(self, server, local_ip, my_uid, group_view, is_leader, network_utils, leader, server_heatbeat_list, server_list):
        self.server = server
        self.local_ip = local_ip
        self.my_uid = my_uid
        self.group_view = group_view
        self.is_leader = is_leader
        self.networkUtils = network_utils
        self.leader = leader
        self.server_list = server_list
        self.server_heatbeat_list = server_heatbeat_list

    #Functions for Leader Election:
    def start_election(self, server):
        #TODO implement leader Election
        print("My UID: ", self.my_uid)
        self.update_serverlist(server)
        if len(self.server_list) == 1:
                self.leader = self.local_ip
                self.is_leader = True
                print("I AM LEADER!")
                return
        ring = self.form_ring(self.server_list)
        neighbour = self.get_neighbour(ring, self.local_ip,'left')

        ringSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ringSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  #changed_remove
        #ringSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  #changed_remove
        #ringSocket.bind((self.local_ip, 5892))
        message = pickle.dumps({"mid": self.my_uid, "isLeader": False, "IP": self.local_ip})
        print("Started election, send message ", pickle.loads(message), "to ", neighbour)
        ringSocket.sendto(message,(neighbour,5892))
        #ringSocket.sendto(message,(neighbour,5892))
        ringSocket.close()

    def election(self, server):
        participant = False
        while True:
            ringSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ringSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #changed_remove
            #ringSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1) #changed_remove
            ringSocket.bind((self.local_ip, 5892))
            self.update_serverlist(server)
            
            ring = self.form_ring(self.server_list)
            neighbour = self.get_neighbour(ring, self.local_ip,'left')
            
            print("Waiting for Election Messages")
            
            data, adress = ringSocket.recvfrom(bufferSize)
            #print (pickle.loads(data))
            self.update_serverlist(server)
            time.sleep(1)
            ring = self.form_ring(self.server_list)
            neighbour = self.get_neighbour(ring, self.local_ip,'left')
            election_message = pickle.loads(data)
            print("Election message:", election_message)
            #print("case 1: ", election_message['mid'] < self.my_uid and not participant, " case2: ", election_message['isLeader'] and ( election_message['mid'] == self.my_uid), " case 3: ", election_message['mid'] < self.my_uid and not participant, " case 4: ", election_message['mid'] > self.my_uid, " case 5: ", election_message['mid'] == self.my_uid)

            if election_message['isLeader'] and not election_message['mid'] == self.my_uid:
                self.leader = election_message['IP']
                print("Leader is: " + self.leader)
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
                    "IP": self.local_ip
                }
                participant = True
                ringSocket.sendto(pickle.dumps(new_election_message),(neighbour,5892))
                print("Send election Message(case 3) ", new_election_message, " to ", neighbour, " at ", time.time())

            elif election_message['mid'] > self.my_uid:
                participant = True
                ringSocket.sendto(data,(neighbour,5892))
                print("Send election Message(case4) ", election_message, " to ", neighbour, " at ", time.time() )

            elif election_message['mid'] == self.my_uid and not election_message['isLeader']:
                self.leader = self.local_ip
                self.is_leader = True
                new_election_message = {
                    "mid": self.my_uid,
                    "isLeader": True,
                    "IP": self.local_ip
                }
                ringSocket.sendto(pickle.dumps(new_election_message),(neighbour,5892))
                print("Send election Message(case5) ", new_election_message, " to ", neighbour, " at ", time.time())
                print("I AM LEADER")
                participant = False   
                ringSocket.close()


    def update_serverlist(self, server):
        self.server_list = []

        for i in self.server.group_view:
            self.server_list.append(i['IP'])
        self.server_list = list(dict.fromkeys(self.server_list))
        #print("UPDATED SERVER LIST : ",self.server_list)

    def form_ring(self, member_list):
        sorted_binary_ring = sorted([socket.inet_aton(member) for member in member_list])
        sorted_ip_ring = [socket.inet_ntoa(node) for node in sorted_binary_ring]
        return sorted_ip_ring
    
    def get_neighbour(self, ring, current_node_ip, direction = 'left'):
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
    def heart_beat_recving(self):
        print('Listen to leader HB ',)
        leader_heartbeat = self.networkUtils.read_client(4444,False,heartbeat_leader=False,heatbeat_server=True)    #fix this port to own heartbeat port
        print("LEADER_HB_ RCCVD",leader_heartbeat)
        if leader_heartbeat:
            if leader_heartbeat[1] == b'heartbeat':
                time.sleep(1)
                thread = threading.Thread(target=self.networkUtils.write_to_client, args=('heartbeat_recvd', self.leader, local_server_port,))    #fix localserverport to leader heartbeat
                thread.start()
                thread.join()
        else:
            if self.is_leader:
                return True
            print('Leader is dead,start election')
            print('Update groupview and election start')
            #if (self.leader_id + 1)%len(self.server.group_view) == self.server_id: 
            new_group_view = []
            dummy_server = None
            for server in self.server.group_view:
                if server['IP'] == self.leader:
                    pass
                else:
                    new_group_view.append(server)
            self.server.group_view = new_group_view
            new_group_view = pickle.dumps(new_group_view)
            self.server.sendto_allServers(dummy_server,new_group_view,5044)
            self.start_election(dummy_server)
            
            if self.is_leader:
                return True
            else:
                #time.sleep(10)
                return False

    def heart_beating(self):
        #time.sleep(10)
        for server in self.server.group_view:
            #time.sleep(10) #heartbeats after 60 seconds
            if self.is_leader == False:
                print('Not leader anymore')
                return True

            server_id = server['serverID']
            server_ip = server['IP']
            server_port = server['heartbeat_port']
            if self.server.leader_for_first_time:
                #print('SET TO ZERO 1')
                self.server_heatbeat_list[server_ip] = 0
                self.server.leader_for_first_time = False
            #print('BEFORE',self.server.group_view)
            if server_ip != self.leader:
                thread = threading.Thread(target=self.networkUtils.write_to_client,args=("heartbeat",server_ip,server_port,))
                thread.start()

                pool = ThreadPool(processes=1)

                
                async_result = pool.apply_async(self.networkUtils.read_client, (local_server_port,False,True,False))  # tuple of args for foo

                # do some other stuff in the main process

                listen_heartbeat = async_result.get()
                print(self.server_heatbeat_list)
                if self.is_leader == False: 
                    return True
                #print("SERVER HB RCVD",listen_heartbeat)
                if listen_heartbeat:
                    if listen_heartbeat[1] == b'heartbeat_recvd':
                        print("Server {} is alive:".format(listen_heartbeat[0][0]))
                        #print('SET TO ZERO 2')
                        self.server_heatbeat_list[listen_heartbeat[0][0]] = 0      #later make this ip
                else:
                    if self.server_heatbeat_list[server_ip] > 3:   #later make this ip and change to 3 tries i.e 2
                        print("Server {} {} is dead:".format(server_ip,server_id))
                        #print("Update Group view and Replicate its clients to new server, choose a new server all this at next heartbeat")
                        #print('SET TO ZERO 3')
                        self.server_heatbeat_list[server_ip] = 0   #later make this ip
                        #inform all other servers
                        new_group_view = []
                        new_client_list = None
                        dummy_server = None
                        for server in self.server.group_view:
                            if server['IP'] == server_ip:
                                new_chatroom = server['chatrooms_handled']
                                pass
                            else:
                                new_group_view.append(server)

                        self.server.group_view = new_group_view
                        min_cli = 10000
                        clients_transfered = False
                        #print('SERVER DEAD, Updated group view: ',self.server.group_view)
                        for servers in self.server.group_view:
                            for chatrooms in servers['chatrooms_handled']:
                                min_cli = min(len(chatrooms['clients_handled']),min_cli)
                        for servers in self.server.group_view:
                            if clients_transfered == True:
                                continue
                            for chatrooms in servers['chatrooms_handled']:
                                #print(chatrooms)
                                if len(chatrooms['clients_handled']) == min_cli:
                                    servers['chatrooms_handled'].append(new_chatroom[0])  #later can be multiple chatrooms so just loop
                                    new_server_ip = servers['IP']
                                    clients_transfered = True
                                    continue
                                else:
                                    min_cli = min(len(chatrooms['clients_handled']),min_cli)
                        # if min_cli != 10000:
                        #     for servers in self.server.group_view:
                        #         for chatrooms in servers['chatrooms_handled']:
                        #             if len(chatrooms['clients_handled']) == min_cli:
                        #                 servers['chatrooms_handled'].append(new_chatroom)
                        #                 new_server_ip = servers['IP']
                        #                 continue


                        #logic to select new sever and append client list
                        #redirect client to new server
                        print("NEW_CLIENT LIST AFTER SERVER DOWN:",new_client_list)
                        print("NEW_GROUP VIEWAFTER SERVER DOWN:",self.server.group_view)
                        new_group_view = pickle.dumps(self.server.group_view)
                        self.server.sendto_allServers(dummy_server, new_group_view, 5044)
                        self.server.send_to_clients_new_server(new_chatroom[0],new_server_ip)
                    self.server_heatbeat_list[server_ip] = self.server_heatbeat_list[server_ip] + 1     #later make this ip

    def heartbeat_mechanism(self):
        while True:   #shud this while loop be inside heartbeating
            
            if self.is_leader:
                is_leader = self.heart_beating()    #should this start new thread
                if is_leader:
                    #self.leader_for_first_time = True
                    print('Not leader anymore')
                    return True
            else:
                is_leader = self.heart_beat_recving()
                #print("HB MECHA:",is_leader,self.server.group_view)
                for server in self.server.group_view:
                    #print('sseeting 0 hereeee')
                    self.server_heatbeat_list[server['IP']] = 0
                if is_leader:
                    #self.leader_for_first_time = True
                    return