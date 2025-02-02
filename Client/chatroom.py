import threading
import time
from queue import Queue
import json

client_inport = 5566
client_outport = 5565

class Chatroom:
    def __init__(self, vector_clock, network_utils, local_ip, server_ip, server_inport, server_outport, userName, leader):
        self.vector_clock = vector_clock
        self.network_utils = network_utils
        self.local_ip = local_ip
        self.server_ip = server_ip
        self.server_inport = server_inport
        self.server_outport = server_outport
        self.userName = userName
        self.leader_election = leader
        self.holdback_q = Queue()

    def hold_back_processing(self):
        try:
            while True:
                if self.holdback_q.empty():
                    self.hold_back_processing()
                else:
                    time.sleep(2) 
                    self.vector_clock.load_vector_clock()
                    list = self.holdback_q.get_nowait()
                    message, rcvd_vc_data, cl_ip, userName = list
                    
                    if self.vector_clock.vector_clock[cl_ip] + 1 == rcvd_vc_data[cl_ip]:
                        self.vector_clock.increment_vector_clock()
                        self.vector_clock.update_vector_clock(rcvd_vc_data, cl_ip)
                        self.vector_clock.save_vector_clock()
                        print(f"🧑‍💻 {userName} : [📤 Out of holdback queue] ", message)
                    else:
                        self.holdback_q.put_nowait([message, rcvd_vc_data, cl_ip, userName])
        except RecursionError:
            self.hold_back_processing()
        except Exception as e:
            print("⚠️ Error in hold_back_processing:", e)

    def chatroom_input(self):
        while True:
            self.leader_election.start_listening(False)
            message_to_send = input("✍️ Please provide your input:")
            if message_to_send == "!exit":
                return True
            else:
                self.vector_clock.load_vector_clock()
                self.vector_clock.increment_vector_clock()
                vc_data = json.dumps(self.vector_clock.vector_clock)
                self.network_utils.send_message(self.server_ip, self.server_inport, "client_id-send_msg-chatroom_id-" + message_to_send + "-" + vc_data + "-" + self.userName)
                data = self.network_utils.recieve_message(client_inport, True)
                if data == b'sent':
                    print("Your message was", data)
                    self.vector_clock.increment_other_clients_vc()
                    self.vector_clock.save_vector_clock()
                elif data == b'resend':
                    time.sleep(1)
                    self.network_utils.send_message(self.server_ip, self.server_inport, "client_id-send_msg-chatroom_id-" + message_to_send + "-" + vc_data + "-" + self.userName)
                    data = self.network_utils.recieve_message(client_outport, True)
                    if data == b'sent':
                        print("Your message was", data)
                        self.vector_clock.increment_other_clients_vc()
                        self.vector_clock.save_vector_clock()
                    elif data == b'resend':
                        print("Please ", data)

    def chatroom_output(self):
        try:
            while True:
                self.leader_election.start_listening(True)
                data = self.network_utils.recieve_message(5565)
                if data:
                    rcvd_msg = data.decode().split("-")
                    message, rcvd_vc_data, cl_ip, userName = rcvd_msg
                    self.vector_clock.load_vector_clock()
                    self.rcvd_vc = json.loads(rcvd_vc_data)
                    neww = self.vector_clock.check_if_new_client(self.rcvd_vc, cl_ip)
                    if self.vector_clock.vector_clock == self.rcvd_vc and cl_ip != self.local_ip and not neww:
                        continue
                    if self.vector_clock.vector_clock == self.rcvd_vc and cl_ip == self.local_ip:
                        print("{}:[OUT]".format(userName), message)
                        time.sleep(1)
                        self.network_utils.send_message(self.server_ip, self.server_outport, "client_id-recvd-" + str(self.server_inport))
                    elif (self.vector_clock.vector_clock[cl_ip] + 1 == self.rcvd_vc[cl_ip] and cl_ip == self.local_ip) or (self.vector_clock.vector_clock[cl_ip] == self.rcvd_vc[cl_ip] and cl_ip == self.local_ip):
                        print("{}:[OUT]".format(userName), message)
                        time.sleep(1)
                        self.vector_clock.update_vector_clock(self.rcvd_vc, cl_ip)
                        self.vector_clock.save_vector_clock()
                        self.network_utils.send_message(self.server_ip, self.server_outport, "client_id-recvd-" + str(self.server_inport))
                    elif self.vector_clock.vector_clock[cl_ip] + 1 == self.rcvd_vc[cl_ip] or self.vector_clock.vector_clock[cl_ip] == self.rcvd_vc[cl_ip]:
                        self.vector_clock.increment_vector_clock()
                        self.vector_clock.update_vector_clock(self.rcvd_vc, cl_ip)
                        self.vector_clock.save_vector_clock()
                        print("{}:[OUT]".format(userName), message)
                        time.sleep(1)
                        self.network_utils.send_message(self.server_ip, self.server_outport, "client_id-recvd-" + str(self.server_inport))
                    else:
                        self.vector_clock.increment_vector_clock()
                        self.vector_clock.save_vector_clock()
                        self.holdback_q.put_nowait([message, self.rcvd_vc, cl_ip, userName])
                        time.sleep(1)
                        self.network_utils.send_message(self.server_ip, self.server_outport, "client_id-recvd-" + str(self.server_inport))
        except Exception as e:
            print("⚠️ Queue exception", e)