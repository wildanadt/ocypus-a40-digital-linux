#!/usr/bin/env python3
"""
ocypus-control.py
---------------------------------
Ocypus Iota A40 LCD driver (Linux / Proxmox)

An improved, object-oriented version for better structure and robustness.

FEATURES
  • Auto-detects the working HID interface.
  • Supports temperature display in Celsius (°C) and Fahrenheit (°F).
  • Works with any psutil sensor.
  • Keeps the panel alive with periodic updates.
  • Includes a command to generate and install a systemd service.
"""

import argparse
import hid
import os
import signal
import sys
import textwrap
import time
from types import FrameType
from typing import List, Dict, Any, Optional, Tuple

import psutil

# --- Constants ---
VID, PID = 0x1a2c, 0x434d
REPORT_ID = 0x07
REPORT_LENGTH = 65
SLOT_TENS, SLOT_ONES = 5, 6
DEFAULT_SENSOR_SUBSTR = "k10temp"
DEFAULT_REFRESH_RATE = 1.0  # seconds
KEEPALIVE_INTERVAL = 2.0  # seconds
UNIT_FLAG_CELSIUS = 0x00
UNIT_FLAG_FAHRENHEIT = 0x01


class OcypusController:
    """Manages the Ocypus Iota A40 LCD device."""

    def __init__(self):
        self.device: Optional[hid.device] = None
        self.interface_number: Optional[int] = None

    def __enter__(self):
        """Context manager entry: opens the device."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: closes the device."""
        self.close()

    @staticmethod
    def find_interfaces() -> List[Dict[str, Any]]:
        """Lists all available Ocypus HID interfaces."""
        return list(hid.enumerate(VID, PID))

    def open(self) -> None:
        """
        Finds and opens a working HID interface for the device.
        Raises:
            IOError: If no working Ocypus interface is found.
        """
        for d in self.find_interfaces():
            try:
                dev = hid.device()
                dev.open_path(d["path"])
                # Test with a harmless blank packet
                dev.write(self._build_blank_report())
                self.device = dev
                self.interface_number = d["interface_number"]
                return
            except hid.HIDException:
                dev.close()
        raise IOError("No working Ocypus interface found (tried all). Ensure script is run with sudo.")

    def close(self) -> None:
        """Blanks the display and closes the HID device."""
        if self.device:
            try:
                self.device.write(self._build_blank_report())
            except hid.HIDException:
                # Device may have been disconnected
                pass
            finally:
                self.device.close()
                self.device = None

    def _build_blank_report(self) -> bytes:
        """Constructs a report to blank the screen."""
        rep = [0] * REPORT_LENGTH
        rep[1:4] = (REPORT_ID, 0xFF, 0xFF)
        return bytes(rep)

    def _build_temp_report(self, value: int, unit_flag: int) -> bytes:
        """
        Constructs a report to display a temperature.
        The firmware automatically shows a leading '1' for temps > 99.
        We only need to send the last two digits (value % 100).
        """
        buf = [0] * REPORT_LENGTH
        buf[1:4] = (REPORT_ID, 0xFF, 0xFF)
        buf[4] = unit_flag
        # The firmware handles the hundreds digit automatically.
        tens = (value // 10) % 10
        ones = value % 10
        buf[SLOT_TENS] = tens
        buf[SLOT_ONES] = ones
        return bytes(buf)

    def run_display_loop(self, sensor_substr: str, unit: str, rate: float) -> None:
        """
        Main loop to read temperature and update the display.
        Args:
            sensor_substr: A substring to identify the temperature sensor.
            unit: 'c' for Celsius or 'f' for Fahrenheit.
            rate: The refresh interval in seconds.
        """
        if not self.device:
            raise RuntimeError("Device is not open. Call open() first.")

        print(f"HID interface {self.interface_number} opened.")
        sensor_name = self._pick_sensor(sensor_substr)
        print(f"Using sensor: {sensor_name}")

        unit_flag = UNIT_FLAG_FAHRENHEIT if unit == "f" else UNIT_FLAG_CELSIUS
        last_val, last_send_time = -1, 0.0
        print("Streaming temperature. Press Ctrl+C to stop.")

        try:
            while True:
                temp_c = self._read_temp(sensor_name)
                temp_display = temp_c if unit == "c" else (temp_c * 9 / 5) + 32
                val = int(round(max(0, min(199, temp_display))))

                now = time.time()
                # Update if value changed or keep-alive interval has passed
                if val != last_val or (now - last_send_time) >= KEEPALIVE_INTERVAL:
                    report = self._build_temp_report(val, unit_flag)
                    self.device.write(report)
                    last_val, last_send_time = val, now
                    unit_char = 'F' if unit_flag == UNIT_FLAG_FAHRENHEIT else 'C'
                    sys.stdout.write(f"\rDisplaying: {val}°{unit_char}   ")
                    sys.stdout.flush()

                time.sleep(max(0.1, rate))
        except (KeyboardInterrupt, RuntimeError) as e:
            print(f"\nExiting: {e}")
        finally:
            self.close()
            print("\nDisplay blanked and device closed.")

    def _pick_sensor(self, substr: str) -> str:
        """
        Selects the best psutil temperature sensor based on a substring.
        Raises:
            RuntimeError: If no matching sensor is found.
        """
        temps = psutil.sensors_temperatures()
        # Prefer exact match
        if substr in temps:
            return substr
        # Fallback to substring match
        for name in temps:
            if substr.lower() in name.lower():
                return name
        raise RuntimeError(f"Sensor containing '{substr}' not found in psutil. Available: {list(temps.keys())}")

    def _read_temp(self, sensor_name: str) -> float:
        """
        Reads the current temperature from a specific sensor.
        Raises:
            RuntimeError: If the sensor has disappeared.
        """
        entry = psutil.sensors_temperatures().get(sensor_name)
        if not entry:
            raise RuntimeError(f"Sensor '{sensor_name}' disappeared.")
        return entry[0].current


def install_systemd_service(unit_name: str, args_line: str) -> None:
    """
    Writes a systemd service file for running the script in the background.
    """
    if os.geteuid() != 0:
        sys.exit("Error: install-service must be run as root.")

    # Use sys.executable for a more robust path to the python interpreter
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    command = f"{python_path} {script_path} {args_line}"
    unit_path = f"/etc/systemd/system/{unit_name}.service"

    unit_content = textwrap.dedent(f"""\
        [Unit]
        Description=Ocypus Iota A40 LCD Monitoring Service
        After=multi-user.target

        [Service]
        Type=simple
        ExecStart={command}
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
    """)

    print(f"Writing systemd unit to {unit_path}...")
    with open(unit_path, "w") as f:
        f.write(unit_content)

    os.system("systemctl daemon-reload")
    print("\nSystemd unit created successfully.")
    print("To enable and start the service, run:")
    print(f"  sudo systemctl enable --now {unit_name}.service")
    print("\nTo check its status, run:")
    print(f"  systemctl status {unit_name}.service")


def main() -> None:
    """Parses command-line arguments and executes the requested command."""
    parser = argparse.ArgumentParser(
        description="Ocypus Iota A40 LCD driver.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # --- 'list' command ---
    subparsers.add_parser("list", help="List all found Ocypus cooler devices.")

    # --- 'on' command ---
    on_parser = subparsers.add_parser("on", help="Turn on the display and stream temperature.")
    on_parser.add_argument("-u", "--unit", choices=["c", "f"], default="c", help="Temperature unit: 'c' for Celsius, 'f' for Fahrenheit.")
    on_parser.add_argument("-s", "--sensor", default=DEFAULT_SENSOR_SUBSTR, help=f"Substring of the psutil sensor to use (default: '{DEFAULT_SENSOR_SUBSTR}').")
    on_parser.add_argument("-r", "--rate", type=float, default=DEFAULT_REFRESH_RATE, help=f"Update interval in seconds (default: {DEFAULT_REFRESH_RATE}).")

    # --- 'off' command ---
    subparsers.add_parser("off", help="Turn off (blank) the display.")

    # --- 'install-service' command ---
    svc_parser = subparsers.add_parser("install-service", help="Install a systemd unit to run the display in the background.")
    svc_parser.add_argument("-u", "--unit", choices=["c", "f"], default="c", help="Temperature unit for the service.")
    svc_parser.add_argument("-s", "--sensor", default=DEFAULT_SENSOR_SUBSTR, help=f"Sensor substring for the service (default: '{DEFAULT_SENSOR_SUBSTR}').")
    svc_parser.add_argument("-r", "--rate", type=float, default=DEFAULT_REFRESH_RATE, help="Update interval for the service.")
    svc_parser.add_argument("--name", default="ocypus-lcd", help="Name for the systemd unit file (default: ocypus-lcd).")

    args = parser.parse_args()

    # --- Command Execution ---
    if args.cmd == "list":
        devs = OcypusController.find_interfaces()
        if not devs:
            print("No Ocypus cooler found.")
            return
        print("Found Ocypus Iota A40 interfaces:")
        for d in devs:
            path = d["path"].decode()
            print(f"  - Interface {d['interface_number']}: {path}")
        return

    if args.cmd == "install-service":
        cli_args = f"on -u {args.unit} -s {args.sensor} -r {args.rate}"
        install_systemd_service(args.name, cli_args)
        return

    try:
        if args.cmd == "off":
            with OcypusController() as controller:
                print(f"HID interface {controller.interface_number} opened.")
                print("Blanking display...")
            print("Display blanked and device closed.")

        elif args.cmd == "on":
            controller = OcypusController()
            # Set up a signal handler for graceful exit on signals like SIGTERM from systemd
            def cleanup_handler(signum: int, frame: Optional[FrameType]):
                print(f"\nSignal {signum} received, shutting down.")
                controller.close()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, cleanup_handler)
            signal.signal(signal.SIGTERM, cleanup_handler)

            controller.open()
            controller.run_display_loop(args.sensor, args.unit, args.rate)

    except (IOError, RuntimeError) as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()