import socket
import subprocess
import ipaddress

def get_local_ip_and_broadcast():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 53))
    IP = s.getsockname()[0]
    proc = subprocess.Popen('ipconfig',stdout=subprocess.PIPE)
    while True:
        line = proc.stdout.readline()
        if IP.encode() in line:
            line = proc.stdout.readline()
            break
    MASK = line.rstrip().split(b':')[-1].replace(b' ',b'').decode()
    host = ipaddress.IPv4Address(IP)
    net = ipaddress.IPv4Network(IP + '/' + MASK, False)
    print(f"🌐 IP: {IP}")
    print(f"🔒 Mask: {MASK}")
    print(f"📡 Subnet: {ipaddress.IPv4Address(int(host) & int(net.netmask))}")
    print(f"💻 Host: {ipaddress.IPv4Address(int(host) & int(net.hostmask))}")
    print(f"📢 Broadcast: {net.broadcast_address}")
    return str(IP),str(net.broadcast_address)