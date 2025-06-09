# Ocypus Iota A40 LCD Driver for Linux/Proxmox

A Python-based driver for controlling the LCD display on Ocypus Iota A40 coolers in Linux environments, including Proxmox.

## ⚠️ Important Disclaimers

- **Hardware Compatibility**: This project was created and tested specifically with the **Ocypus Iota A40** cooler only
- **Limited Testing**: The driver has only been tested on a specific hardware configuration
- **Hardware Detection**: The device appears in `lsusb` as:
  ```
  ID 1a2c:434d China Resource Semico Co., Ltd USB Gaming Keyboard
  Manufacturer: SEMICO
  Product: USB Gaming Keyboard
  ```
- **Use at Your Own Risk**: While the driver is designed to be safe, use it at your own discretion
- **Community Contribution**: This is a community-created project, not officially supported by Ocypus

## Development Note

This driver was developed by the community specifically for the Ocypus Iota A40 cooler. The hardware identification shows as a "USB Gaming Keyboard" from China Resource Semico Co., Ltd, which is the actual manufacturer of the LCD controller used in the Ocypus A40.

## Features

- **Auto-detection**: Automatically detects and connects to working HID interfaces
- **Temperature Display**: Shows real-time CPU temperature on the cooler's LCD
- **Dual Units**: Supports both Celsius (°C) and Fahrenheit (°F) temperature display
- **Sensor Flexibility**: Works with any psutil-compatible temperature sensor
- **Keep-alive**: Maintains display connection with periodic updates
- **Systemd Integration**: Built-in command to generate and install systemd service
- **Robust Design**: Object-oriented architecture with proper error handling

## Requirements

- Python 3.6+
- Linux operating system (tested on Ubuntu, Debian, Proxmox)
- Root privileges (required for HID device access)
- Dependencies:
  - `hidapi`
  - `psutil`

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/moyunkz/ocypus-a40-digital-linux.git
   cd ocypus-a40-digital-linux
   ```

2. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Make the script executable:**
   ```bash
   chmod +x ocypus-control.py
   ```

## Usage

### Basic Commands

**List available Ocypus devices:**
```bash
sudo ./ocypus-control.py list
```

**Turn on temperature display (Celsius):**
```bash
sudo ./ocypus-control.py on
```

**Turn on temperature display (Fahrenheit):**
```bash
sudo ./ocypus-control.py on -u f
```

**Turn off/blank the display:**
```bash
sudo ./ocypus-control.py off
```

### Advanced Options

**Specify a custom sensor:**
```bash
sudo ./ocypus-control.py on -s "coretemp" -u c
```

**Set custom refresh rate (in seconds):**
```bash
sudo ./ocypus-control.py on -r 2.0
```

**Full command with all options:**
```bash
sudo ./ocypus-control.py on -u f -s "k10temp" -r 1.5
```

### Systemd Service Installation

**Install as a systemd service:**
```bash
sudo ./ocypus-control.py install-service
```

**Install with custom settings:**
```bash
sudo ./ocypus-control.py install-service -u f -s "coretemp" -r 2.0 --name my-ocypus
```

**Enable and start the service:**
```bash
sudo systemctl enable --now ocypus-lcd.service
```

**Check service status:**
```bash
systemctl status ocypus-lcd.service
```

## Command Reference

### Main Commands

| Command | Description |
|---------|-------------|
| `list` | List all found Ocypus cooler devices |
| `on` | Turn on display and stream temperature |
| `off` | Turn off (blank) the display |
| `install-service` | Install systemd unit for background operation |

### Options for `on` command

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--unit` | `-u` | `c` | Temperature unit: 'c' for Celsius, 'f' for Fahrenheit |
| `--sensor` | `-s` | `k10temp` | Substring of psutil sensor to use |
| `--rate` | `-r` | `1.0` | Update interval in seconds |

### Options for `install-service` command

| Option | Default | Description |
|--------|---------|-------------|
| `--unit` | `c` | Temperature unit for the service |
| `--sensor` | `k10temp` | Sensor substring for the service |
| `--rate` | `1.0` | Update interval for the service |
| `--name` | `ocypus-lcd` | Name for the systemd unit file |

## Technical Details

### Hardware Compatibility
- **Vendor ID**: 0x1a2c
- **Product ID**: 0x434d
- **Interface**: HID (Human Interface Device)

### Temperature Display
- **Format**: 2-digit display with temperature unit indicator
- **Units**: Supports both Celsius (°C) and Fahrenheit (°F)

### Sensor Detection
The script uses psutil to detect temperature sensors. Common sensor names include:
- `k10temp` (AMD processors)
- `coretemp` (Intel processors)
- `acpi` (ACPI thermal zones)

## Troubleshooting

### Permission Issues
```
Error: No working Ocypus interface found
```
**Solution**: Ensure you're running the script with `sudo` privileges.

### Sensor Not Found
```
Sensor containing 'k10temp' not found
```
**Solution**: 
1. List available sensors: `python3 -c "import psutil; print(psutil.sensors_temperatures().keys())"`
2. Use the correct sensor name with `-s` option

### Device Not Detected
```
No Ocypus cooler found
```
**Solution**:
1. Check USB connection
2. Verify device compatibility
3. Try different USB ports

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for the Ocypus Iota A40 cooler community
- Uses psutil for cross-platform temperature monitoring
- Implements HID communication for direct hardware control