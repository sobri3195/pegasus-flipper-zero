#!/usr/bin/env python3
"""
Flipper Zero Bluetooth Keyboard Spy Script
For monitoring nearby devices without touching or installing anything

Requirements:
- Latest stable firmware installed on Flipper Zero with Developer Board
"""

import serial
import time
import bluetooth
import subprocess

def activate_hid_mode():
    """Activate HID keyboard emulation mode"""
    ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
    
    # Send HID activation sequence
    hid_sequence = bytes([0x06, 0x2b, 0x85, 0x74])
    for byte in hid_sequence:
        ser.write(bytes([byte]))
    
    print("[+] Activated keyboard mode")
    return ser

def scan_bluetooth_devices():
    """Scan and list nearby Bluetooth devices"""
    try:
        # Start scanning
        subprocess.run(['bluetoothctl', 'scan', 'on'], check=True)
        
        # Scan for 10 seconds
        time.sleep(10)
        
        # Stop scanning
        subprocess.run(['bluetoothctl', 'scan', 'off'], check=True)
        
        # Get device list
        output = subprocess.check_output(
            ['bluetoothctl', 'devices'], 
            universal_newlines=True
        )
        
        print("[+] Bluetooth devices found:")
        for line in output.splitlines():
            if "Device" in line:
                parts = line.strip().split()
                mac_addr, name = parts[2], parts[-1]
                print(f"    {mac_addr}: {name}")
                
    except subprocess.CalledProcessError as e:
        print("[-] Bluetooth scan error:", str(e))

def main():
    try:
        # Activate HID mode first
        ser = activate_hid_mode()
        
        # Wait for keyboard setup complete
        time.sleep(5)
        
        # Scan nearby devices
        scan_bluetooth_devices()
        
        # Close serial connection
        ser.close()
        
    except KeyboardInterrupt:
        print("\n[!] Exiting...")
    
if __name__ == "__main__":
    main()

def track_connections():
    """Track connections and disconnections"""
    # Add timestamp tracking for each connection/disconnection event
    conn_log = open('connection.log', 'a')
    
    def on_connection(mac_addr, name):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        conn_log.write(f"{timestamp} - CONNECTED: {mac_addr}: {name}\n")
        
    # Hook into Bluetooth events
    subprocess.Popen(['bluetoothctl', 'scan', 'on'])

def measure_signal_strength():
    """Measure signal strength of nearby devices"""
    output = subprocess.check_output(
        ['hcitool', 'inquiry'], 
        universal_newlines=True
    )
    
    print("[+] Signal strengths:")
    for line in output.splitlines()[1:]:  # Skip header
        if "INQ:" not in line:
            parts = line.strip().split()
            mac_addr, name = parts[2], parts[-1]
            rssi = parts[3].replace(')', '')
            print(f"    {mac_addr}: {name} - RSSI: {rssi}")

      def capture_audio():
    """Capture audio from paired devices"""
    # Enable microphone access through ALSA
    subprocess.run(['amixer', 'set', 'Mic', '100%'], check=True)
    
    # Start recording to file
    with open('audio.pcm', 'wb') as f:
        subprocess.Popen(
            ['arecord', '-f', 'S16_LE', '-r', '48000', '-d', '30'],
            stdout=f, stderr=subprocess.DEVNULL
        )
