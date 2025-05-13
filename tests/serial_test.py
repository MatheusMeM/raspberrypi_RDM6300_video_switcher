#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import time
import sys

# --- Configuration ---
SERIAL_PORT = '/dev/serial0'  #  Default for Raspberry Pi hardware UART
BAUD_RATE = 9600
# ---------------------

print("--- RDM6300 Serial Test ---")
print(f"Attempting to open serial port: {SERIAL_PORT} at {BAUD_RATE} baud.")
print("Please present an RFID tag to the reader.")
print("Press Ctrl+C to exit.")
print("---------------------------")

ser = None  # Initialize ser to None

try:
    # Initialize and open the serial port
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0.5  # Read timeout in seconds (0.5 is usually good)
    )
    print(f"Serial port {SERIAL_PORT} opened successfully.")

    while True:
        # Check if there is data waiting in the serial buffer
        if ser.in_waiting > 0:
            # Read all available bytes
            incoming_bytes = ser.read(ser.in_waiting)

            print(f"Received {len(incoming_bytes)} bytes:")

            # Print raw bytes (useful for debugging non-ASCII data)
            print(f"  Raw Bytes: {incoming_bytes}")

            # Attempt to decode as ASCII (RDM6300 often sends ASCII hex digits)
            try:
                # Use errors='ignore' to avoid crashing on non-ASCII start/stop bytes
                decoded_string = incoming_bytes.decode('ascii', errors='ignore')
                # .strip() removes leading/trailing whitespace including potential newlines
                print(f"  Decoded ASCII (approx): '{decoded_string.strip()}'")
            except Exception as decode_error:
                print(f"  Could not decode as ASCII: {decode_error}")

            print("-" * 20) # Separator for readability

        # Small delay to prevent hogging CPU
        time.sleep(0.05)

except serial.SerialException as e:
    print(f"\n[ERROR] Could not open or read from serial port {SERIAL_PORT}.")
    print(f"  Error message: {e}")
    print("  Troubleshooting:")
    print("    - Is the RDM6300 powered and correctly wired (TX->LevelShifter->Pi RX)?")
    print(f"    - Is the serial port '{SERIAL_PORT}' correct?")
    print("    - Is Hardware Serial enabled in 'sudo raspi-config' (and console disabled)?")
    print(f"    - Does the user running this script belong to the 'dialout' group? (Current user: {sys.argv[0]})")
    print("      (Run 'groups' command to check. Add with 'sudo usermod -aG dialout <username>' and reboot/re-login)")
except KeyboardInterrupt:
    print("\n[INFO] Ctrl+C detected. Exiting program.")
except Exception as general_error:
    print(f"\n[ERROR] An unexpected error occurred: {general_error}")
finally:
    # Ensure the serial port is closed even if an error occurs
    if ser and ser.is_open:
        ser.close()
        print(f"[INFO] Serial port {SERIAL_PORT} closed.")

print("--- Test script finished ---")