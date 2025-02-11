import json

class VectorClock:
    def __init__(self, local_ip):
        self.vector_clock = {}
        self.local_ip = local_ip

    def update_vector_clock(self, rcvd_vc, cl_ip):
        for ip, value in rcvd_vc.items():
            if cl_ip not in self.vector_clock:
                self.vector_clock[cl_ip] = value
            else:
                self.vector_clock[ip] = max(self.vector_clock[ip], rcvd_vc[ip])

    def check_if_new_client(self, rcvd_vc, cl_ip):
        if cl_ip not in self.vector_clock:
            self.vector_clock[cl_ip] = rcvd_vc[cl_ip]
            return True
        return False

    def init_own_vector(self):
        if self.local_ip not in self.vector_clock:
            self.vector_clock[self.local_ip] = 0
        self.save_vector_clock()

    def increment_vector_clock(self):
        if self.local_ip not in self.vector_clock:
            self.vector_clock[self.local_ip] = 0
        self.vector_clock[self.local_ip] += 1

    def decrement_vector_clock(self):
        if self.local_ip not in self.vector_clock:
            self.vector_clock[self.local_ip] = 0
        self.vector_clock[self.local_ip] -= 1

    def save_vector_clock(self):
        with open("vector_clock.json", "w") as file:
            json.dump(self.vector_clock, file)

    def load_vector_clock(self):
        with open("vector_clock.json", "r") as file:
            self.vector_clock = json.load(file)

    def increment_other_clients_vc(self):
        for ip in self.vector_clock:
            if ip != self.local_ip:
                self.vector_clock[ip] += 1

    def init_vector_clock(self):
        self.load_vector_clock()
        self.vector_clock = {ip: 0 for ip in self.vector_clock}
        self.save_vector_clock()