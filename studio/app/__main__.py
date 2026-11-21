"""Start the studio: `python -m app`."""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import webbrowser


def _free_port(start: int) -> int:
    for port in range(start, start + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # on Windows SO_REUSEADDR would let the bind succeed on a port that is already taken
            if os.name == "nt":
                s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", socket.SO_REUSEADDR), 1)
            else:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return start


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="הסטודיו שלי")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="0.0.0.0", help="127.0.0.1 = this computer only")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    import uvicorn

    from . import config, server

    config.ensure_dirs()
    config.load_settings()
    port = _free_port(args.port)
    server.PORT["value"] = port
    server.recover_interrupted()
    local = f"http://localhost:{port}"
    print()
    print("  Studio is running")
    print(f"  On this computer:  {local}")
    if args.host != "127.0.0.1":
        ip = server.lan_ip()
        if ip:
            print(f"  From your phone:   open the studio here and scan the QR code (same Wi-Fi), {ip}:{port}")
    print("  To stop: close this window, or press Ctrl+C")
    print()
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(local)).start()
    uvicorn.run(server.app, host=args.host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
