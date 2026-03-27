#!/usr/bin/env python3
"""Flipper Zero + Bluetooth diagnostics utility.

This script focuses on **local diagnostics** and observability:
- optional Flipper serial handshake
- Bluetooth scan for nearby devices
- optional connection-event logging (poll-based)
- optional RSSI inquiry output

It avoids intrusive actions and requires explicit CLI flags per feature.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import platform
import socket
import sys
import time
from pathlib import Path
from typing import Iterable

from flipper_core import CommandError, Device, parse_devices, run_command


def activate_hid_mode(port: str, baudrate: int = 115200, timeout: int = 1):
    """Send a simple serial handshake sequence to the configured serial port."""
    serial_module = importlib.import_module("serial")
    ser = serial_module.Serial(port, baudrate, timeout=timeout)
    hid_sequence = bytes([0x06, 0x2B, 0x85, 0x74])
    ser.write(hid_sequence)
    print(f"[+] Handshake sent to {port} at {baudrate} bps")
    return ser


def scan_bluetooth_devices(scan_seconds: int) -> list[Device]:
    """Scan for nearby Bluetooth devices and return parsed results."""
    print(f"[*] Scanning Bluetooth devices for {scan_seconds}s...")
    run_command(["bluetoothctl", "scan", "on"])
    try:
        time.sleep(scan_seconds)
    finally:
        run_command(["bluetoothctl", "scan", "off"])

    output = run_command(["bluetoothctl", "devices"])
    devices = parse_devices(output)

    if not devices:
        print("[-] No Bluetooth devices discovered.")
        return devices

    print(f"[+] Found {len(devices)} device(s):")
    for item in devices:
        print(f"    {item.mac}: {item.name}")
    return devices


def get_current_connections() -> set[str]:
    """Return currently connected device MAC addresses from bluetoothctl info."""
    devices = parse_devices(run_command(["bluetoothctl", "devices"]))
    connected: set[str] = set()

    for dev in devices:
        info = run_command(["bluetoothctl", "info", dev.mac], check=False)
        if "Connected: yes" in info:
            connected.add(dev.mac)

    return connected


def track_connections(log_file: Path, duration_seconds: int, poll_interval: int) -> None:
    """Track connection/disconnection events and append to a log file."""
    print(
        f"[*] Tracking connection events for {duration_seconds}s "
        f"(interval={poll_interval}s)"
    )

    previous = get_current_connections()
    end_time = time.time() + duration_seconds

    with log_file.open("a", encoding="utf-8") as fh:
        while time.time() < end_time:
            time.sleep(poll_interval)
            current = get_current_connections()

            connected_now = sorted(current - previous)
            disconnected_now = sorted(previous - current)

            timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for mac in connected_now:
                line = f"{timestamp} - CONNECTED: {mac}"
                print(f"[+] {line}")
                fh.write(line + "\n")

            for mac in disconnected_now:
                line = f"{timestamp} - DISCONNECTED: {mac}"
                print(f"[-] {line}")
                fh.write(line + "\n")

            fh.flush()
            previous = current


def measure_signal_strength() -> None:
    """Display RSSI lines from hcitool inquiry if available."""
    output = run_command(["hcitool", "inquiry"], check=False)
    if not output:
        print("[-] No RSSI inquiry output (adapter unavailable or no devices).")
        return

    print("[+] RSSI inquiry output:")
    for line in output.splitlines():
        print(f"    {line}")


def list_paired_devices() -> list[Device]:
    """Show paired devices from bluetoothctl."""
    devices = parse_devices(run_command(["bluetoothctl", "paired-devices"], check=False))
    if not devices:
        print("[-] No paired devices found.")
        return []

    print(f"[+] Paired devices ({len(devices)}):")
    for item in devices:
        print(f"    {item.mac}: {item.name}")
    return devices


def show_adapters() -> None:
    """Show available Bluetooth adapters and status hints."""
    output = run_command(["bluetoothctl", "list"], check=False)
    if not output:
        print("[-] No adapter data from bluetoothctl list.")
        return

    print("[+] Bluetooth adapters:")
    for line in output.splitlines():
        print(f"    {line}")


def set_adapter_power(power_on: bool) -> None:
    """Turn default Bluetooth adapter power on/off."""
    state = "on" if power_on else "off"
    result = run_command(["bluetoothctl", "power", state], check=False)
    print(f"[+] Adapter power {state}: {result or 'ok'}")


def remove_device(mac: str) -> None:
    """Remove a paired device by MAC address."""
    result = run_command(["bluetoothctl", "remove", mac], check=False)
    print(f"[+] Remove result for {mac}: {result or 'ok'}")


def print_device_info(mac: str) -> None:
    """Print detailed info for a specific MAC address."""
    info = run_command(["bluetoothctl", "info", mac], check=False)
    if not info:
        print(f"[-] No info found for {mac}.")
        return
    print(f"[+] Device info for {mac}:")
    for line in info.splitlines():
        print(f"    {line}")


def export_devices_json(output_path: Path) -> None:
    """Export discovered devices to JSON file."""
    devices = parse_devices(run_command(["bluetoothctl", "devices"], check=False))
    payload = [{"mac": d.mac, "name": d.name} for d in devices]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[+] Exported {len(payload)} device(s) to {output_path}")


def ping_host(host: str, timeout_seconds: int) -> None:
    """Check whether TCP/443 is reachable for a host."""
    print(f"[*] Checking TCP connectivity to {host}:443 (timeout={timeout_seconds}s)...")
    with socket.create_connection((host, 443), timeout=timeout_seconds):
        print(f"[+] Host {host} reachable on port 443")


def print_system_report() -> None:
    """Print simple local environment report for diagnostics."""
    uname = platform.uname()
    report = {
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
        "platform": platform.platform(),
        "system": uname.system,
        "release": uname.release,
        "machine": uname.machine,
        "python": sys.version.split()[0],
    }

    hciconfig = run_command(["hciconfig"], check=False)
    report["hciconfig_available"] = bool(hciconfig)
    report["adapter_snapshot"] = hciconfig.splitlines()[:8] if hciconfig else []

    print("[+] System report:")
    print(json.dumps(report, indent=2))


def monitor_devices(duration_seconds: int, poll_interval: int) -> None:
    """Monitor discovered-device count over time."""
    print(
        f"[*] Monitoring device count for {duration_seconds}s "
        f"(interval={poll_interval}s)"
    )
    end_time = time.time() + duration_seconds
    while time.time() < end_time:
        devices = parse_devices(run_command(["bluetoothctl", "devices"], check=False))
        timestamp = dt.datetime.now().strftime("%H:%M:%S")
        print(f"[i] {timestamp} | discovered_devices={len(devices)}")
        time.sleep(poll_interval)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Flipper Zero Bluetooth diagnostics utility"
    )
    parser.add_argument(
        "--serial-port",
        default="/dev/ttyACM0",
        help="Serial port for Flipper handshake (default: /dev/ttyACM0)",
    )
    parser.add_argument(
        "--activate-hid",
        action="store_true",
        help="Send handshake bytes to Flipper over serial port",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Run Bluetooth device scan",
    )
    parser.add_argument(
        "--scan-seconds",
        type=positive_int,
        default=10,
        help="Duration for Bluetooth scan in seconds (default: 10)",
    )
    parser.add_argument(
        "--track-connections",
        action="store_true",
        help="Track connection/disconnection events",
    )
    parser.add_argument(
        "--track-seconds",
        type=positive_int,
        default=30,
        help="How long to track connections in seconds (default: 30)",
    )
    parser.add_argument(
        "--poll-interval",
        type=positive_int,
        default=3,
        help="Polling interval for connection tracking (default: 3)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("connection.log"),
        help="File path for connection logs (default: connection.log)",
    )
    parser.add_argument(
        "--rssi",
        action="store_true",
        help="Print RSSI inquiry output (requires hcitool)",
    )

    # 10 new features
    parser.add_argument(
        "--list-paired",
        action="store_true",
        help="List paired Bluetooth devices",
    )
    parser.add_argument(
        "--show-adapters",
        action="store_true",
        help="List available Bluetooth adapters",
    )
    parser.add_argument(
        "--adapter-power-on",
        action="store_true",
        help="Turn Bluetooth adapter power on",
    )
    parser.add_argument(
        "--adapter-power-off",
        action="store_true",
        help="Turn Bluetooth adapter power off",
    )
    parser.add_argument(
        "--remove-device",
        metavar="MAC",
        help="Remove paired device by MAC address",
    )
    parser.add_argument(
        "--device-info",
        metavar="MAC",
        help="Show detailed information for a device MAC address",
    )
    parser.add_argument(
        "--export-devices-json",
        type=Path,
        metavar="PATH",
        help="Export discovered devices to JSON file",
    )
    parser.add_argument(
        "--ping-host",
        metavar="HOST",
        help="Check TCP connectivity to HOST on port 443",
    )
    parser.add_argument(
        "--system-report",
        action="store_true",
        help="Print local system diagnostic report",
    )
    parser.add_argument(
        "--monitor-devices",
        action="store_true",
        help="Monitor discovered-device count over time",
    )
    parser.add_argument(
        "--ping-timeout",
        type=positive_int,
        default=3,
        help="Timeout for --ping-host in seconds (default: 3)",
    )
    return parser


def run_selected_features(args: argparse.Namespace) -> int:
    """Execute selected features and return process exit code."""
    serial_conn = None
    try:
        if args.activate_hid:
            serial_conn = activate_hid_mode(args.serial_port)

        if args.scan:
            scan_bluetooth_devices(args.scan_seconds)

        if args.track_connections:
            track_connections(args.log_file, args.track_seconds, args.poll_interval)

        if args.rssi:
            measure_signal_strength()

        if args.list_paired:
            list_paired_devices()

        if args.show_adapters:
            show_adapters()

        if args.adapter_power_on:
            set_adapter_power(True)

        if args.adapter_power_off:
            set_adapter_power(False)

        if args.remove_device:
            remove_device(args.remove_device)

        if args.device_info:
            print_device_info(args.device_info)

        if args.export_devices_json:
            export_devices_json(args.export_devices_json)

        if args.ping_host:
            ping_host(args.ping_host, args.ping_timeout)

        if args.system_report:
            print_system_report()

        if args.monitor_devices:
            monitor_devices(args.track_seconds, args.poll_interval)

        if not any(
            (
                args.activate_hid,
                args.scan,
                args.track_connections,
                args.rssi,
                args.list_paired,
                args.show_adapters,
                args.adapter_power_on,
                args.adapter_power_off,
                bool(args.remove_device),
                bool(args.device_info),
                bool(args.export_devices_json),
                bool(args.ping_host),
                args.system_report,
                args.monitor_devices,
            )
        ):
            print("[i] No feature selected. Use --help to see available options.")

        return 0
    except (CommandError, OSError, ModuleNotFoundError, ValueError) as exc:
        print(f"[-] {exc}", file=sys.stderr)
        return 1
    finally:
        if serial_conn is not None:
            serial_conn.close()


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_selected_features(args)


if __name__ == "__main__":
    raise SystemExit(main())
