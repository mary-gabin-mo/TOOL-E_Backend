"""
PURPOSE:
Standalone smartcard reader polling test for validating PC/SC setup on device.

RUNTIME ROLE:
- Developer utility script; not used by kiosk runtime app.

API ENDPOINTS USED:
- None.
"""

from smartcard.System import readers
from smartcard.util import toHexString
import time

print("--- Simple Pyscard Test ---")

# List Readers
r = readers()
print(f"Readers found: {r}")

if len(r) == 0:
    print("Error: No readers found via Python.")
    exit()

reader = r[0]
print(f"Using: {reader}")

# Polling Loop
print("Please tap a card now (Ctrl+C to stop)...")

while True:
    try:
        connection = reader.createConnection()
        connection.connect()
	
	# Send Command (Get UID)
	# Standard Mifare Get UID command
        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        data, sw1, sw2 = connection.transmit(GET_UID)

        if sw1 == 0x90:
            uid = toHexString(data)
            print(f"SUCCESS! Card UID: {uid} {hex(sw1)} {hex(sw2)}")
        else:
            print(f"Card found, but command failed. {uid=} Status: {hex(sw1)} {hex(sw2)}")
    
    except Exception as e:
	# This usually happens when no card is present
	# Uncomment next line to see noise errors:
	# print(f"Polling... ({e})")
        pass

    time.sleep(0.5)
