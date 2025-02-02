import threading
from vector_clock import VectorClock
from network_utils import NetworkUtils
from chatroom import Chatroom
from authentication import Authentication
from listenToLeader import ListernToLeader
from dynamic_ip import get_local_ip_and_broadcast

MY_IP, BROADCAST_IP = get_local_ip_and_broadcast()

class Client:
    def __init__(self):
        self.vector_clock = VectorClock(MY_IP)
        self.network_utils = NetworkUtils(MY_IP)
        self.authentication = Authentication(MY_IP, BROADCAST_IP, 10001)
        self.listenToLeader = ListernToLeader(MY_IP)
        self.server_ip = ''
        self.server_inport = 0
        self.server_outport = 0
        self.userName = ''

    def after_login(self):
        """
        Handles post-login functionality, including chatroom input/output.
        """
        selection = input("Which window you prefer to enter? \n 1️⃣ Output Window \n 2️⃣ Input Window \n")
        if selection == '1':
            hold_back_processing_thread = threading.Thread(target=self.chatroom.hold_back_processing, args=())
            hold_back_processing_thread.start()
            self.chatroom.chatroom_output()
        elif selection == '2':
            # Start listening for leader updates in the background
            self.listenToLeader.start_listening(False)
            client_id = input("Give Your ID:")
            self.chatroom.chatroom_input()

    def login(self, userName):
        """
        Handles user login and server selection.
        """
        self.userName = userName
        self.server_ip, self.server_inport, self.server_outport = self.authentication.login(userName)
        self.vector_clock.init_own_vector()
        self.vector_clock.init_vector_clock()
        self.chatroom = Chatroom(self.vector_clock, self.network_utils, MY_IP, self.server_ip, self.server_inport, self.server_outport, self.userName, self.listenToLeader)

if __name__ == '__main__':
    client = Client()
    userName = input('Enter UserName: ')
    client.login(userName)
    
    while True:
        p_chat = threading.Thread(target=client.after_login)
        p_chat.start()
        p_chat.join()