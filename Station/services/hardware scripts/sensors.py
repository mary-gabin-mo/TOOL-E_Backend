"""
PURPOSE:
Standalone load-cell + camera trigger prototype script.

RUNTIME ROLE:
- Developer hardware test utility; not imported by kiosk runtime app.

API ENDPOINTS USED:
- None.
"""

import time
import lgpio
from single_capt import init_camera, take_picture, close_camera

# -----------------------------
# HX711 wiring
# -----------------------------
DOUT_PIN = 5   # DOUT → GPIO 5
SCK_PIN  = 6   # SCK  → GPIO 6


CHIP = 0  # /dev/gpiochip0

# -----------------------------
# Detection parameters
# -----------------------------
READ_INTERVAL     = 0.1
STABLE_READS      = 3
OBJECT_THRESHOLD  = 1000 # minimum raw weight
REMOVAL_FACTOR    = 0.5   

# -----------------------------
# Setup GPIO
# -----------------------------
handle = lgpio.gpiochip_open(CHIP)
lgpio.gpio_claim_input(handle, DOUT_PIN)
lgpio.gpio_claim_output(handle, SCK_PIN, 0)

# -----------------------------
# HX711 low-level read
# -----------------------------
def hx711_read_raw():
    while lgpio.gpio_read(handle, DOUT_PIN) == 1:
        time.sleep(0.0001)

    value = 0
    for _ in range(24):
        lgpio.gpio_write(handle, SCK_PIN, 1)
        value = (value << 1) | lgpio.gpio_read(handle, DOUT_PIN)
        lgpio.gpio_write(handle, SCK_PIN, 0)

    lgpio.gpio_write(handle, SCK_PIN, 1)
    lgpio.gpio_write(handle, SCK_PIN, 0)

    if value & 0x800000:
        value -= 1 << 24

    return value

# no object value was this. will change after knowing weight of placing area
offset = 382000

def get_raw_weight():
    return hx711_read_raw() - offset



# -----------------------------
# Wait for object / removal
# -----------------------------
def wait_for_object():
    print("Waiting for object...")
    stable = 0
    last_weight = 0

    while True:
        w = get_raw_weight()
        last_weight = w

        if w > OBJECT_THRESHOLD:
            stable += 1
        else:
            stable = 0

        if stable >= STABLE_READS:
            print(f"Object detected! Raw weight: {last_weight:.0f}")
            return

        time.sleep(READ_INTERVAL)


def wait_for_removal():
    removed_level = OBJECT_THRESHOLD * REMOVAL_FACTOR
    print("Waiting for object removal...")
    while True:
        w = get_raw_weight()

        if w < removed_level:
            print("Object removed. Exiting.")
            return

        time.sleep(READ_INTERVAL)

# -----------------------------
# MAIN (single cycle)
# -----------------------------
if __name__ == "__main__":
    
    init_camera()

    try:
        # Run ONE borrow cycle, then exit
        wait_for_object()
        take_picture()
        wait_for_removal()

    except KeyboardInterrupt:
        print("Interrupted by user.")

    finally:
        close_camera()
        lgpio.gpiochip_close(handle)
        print("Clean exit.")
