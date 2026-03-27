"""Core helpers for Flipper Zero Bluetooth diagnostics utility."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    """A Bluetooth device discovered by bluetoothctl."""

    mac: str
    name: str


class CommandError(RuntimeError):
    """Raised when a shell command fails."""


def run_command(cmd: list[str], *, check: bool = True) -> str:
    """Run a command and return stdout as text."""
    try:
        completed = subprocess.run(
            cmd,
            check=check,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise CommandError(f"Command not found: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or str(exc)
        raise CommandError(
            f"Command failed ({' '.join(shlex.quote(x) for x in cmd)}): {detail}"
        ) from exc

    return completed.stdout.strip()


def parse_devices(output: str) -> list[Device]:
    """Parse output from `bluetoothctl devices` style command."""
    devices: list[Device] = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("Device "):
            continue

        parts = line.split(maxsplit=2)
        if len(parts) < 3:
            continue

        _, mac, name = parts
        devices.append(Device(mac=mac, name=name))

    return devices
