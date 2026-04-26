"""
Serial -> UDP bridge for the Hackabull glove (Node B).

Reads JSON lines printed by the glove's Arduino sketch over USB serial
and forwards each one as a UDP datagram to the backend's IMU port
(127.0.0.1:9002 by default), so the backend never knows the difference
between a real WiFi-pushed packet and a serial-bridged one.

Usage:
    python scripts/serial_bridge.py --port COM5
    python scripts/serial_bridge.py --port COM5 --baud 115200 --target 127.0.0.1:9002
    python scripts/serial_bridge.py --list           # list available serial ports
"""

import argparse
import json
import socket
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.stderr.write(
        "pyserial is required. Install with: .venv\\Scripts\\python -m pip install pyserial\n"
    )
    sys.exit(1)


def list_serial_ports() -> None:
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return
    print(f"{'Port':<8} {'Description':<50} Hardware ID")
    print("-" * 100)
    for p in ports:
        print(f"{p.device:<8} {p.description:<50} {p.hwid}")


def parse_target(target: str) -> tuple[str, int]:
    host, _, port = target.partition(":")
    if not port:
        raise ValueError(f"target must be host:port, got {target!r}")
    return host, int(port)


def run_bridge(port: str, baud: int, host: str, udp_port: int, verbose: bool) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[bridge] forwarding {port}@{baud} -> {host}:{udp_port}")

    while True:
        try:
            with serial.Serial(port, baud, timeout=1) as ser:
                print(f"[bridge] opened {port}")
                ser.reset_input_buffer()
                packets = 0
                t0 = time.time()
                while True:
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="ignore").strip()
                    if not line or not line.startswith("{"):
                        # Skip boot/debug lines like "WiFi connected, IP: ..."
                        if verbose and line:
                            print(f"[bridge] (skip) {line}")
                        continue
                    try:
                        # Validate JSON shape so we don't forward garbage
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        if verbose:
                            print(f"[bridge] (bad json) {line}")
                        continue

                    sock.sendto(line.encode("utf-8"), (host, udp_port))
                    packets += 1
                    if verbose:
                        print(f"[bridge] {obj}")
                    elif packets % 50 == 0:
                        rate = packets / (time.time() - t0)
                        print(f"[bridge] forwarded {packets} packets ({rate:.1f}/s)")
        except serial.SerialException as exc:
            print(f"[bridge] serial error: {exc}. Retrying in 2s...")
            time.sleep(2)
        except KeyboardInterrupt:
            print("\n[bridge] stopped by user.")
            return


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="Serial port (e.g. COM5 on Windows, /dev/ttyUSB0 on Linux)")
    ap.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    ap.add_argument("--target", default="127.0.0.1:9002", help="UDP target host:port (default: 127.0.0.1:9002)")
    ap.add_argument("--verbose", "-v", action="store_true", help="Print every forwarded packet")
    ap.add_argument("--list", action="store_true", help="List available serial ports and exit")
    args = ap.parse_args()

    if args.list:
        list_serial_ports()
        return

    if not args.port:
        ap.error("--port is required (or use --list to see available ports)")

    host, udp_port = parse_target(args.target)
    run_bridge(args.port, args.baud, host, udp_port, args.verbose)


if __name__ == "__main__":
    main()
