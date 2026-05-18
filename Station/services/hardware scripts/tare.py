# pyright: reportMissingImports=false

"""
PURPOSE:
Standalone load-cell tare utility for capturing the empty-bed offset.

RUNTIME ROLE:
- Developer hardware calibration script; not imported by kiosk runtime app.

API ENDPOINTS USED:
- None.
"""

import time

import lgpio

# -----------------------------
# HX711 wiring
# -----------------------------
DOUT_PIN = 5   # DOUT -> GPIO 5
SCK_PIN = 6    # SCK  -> GPIO 6
CHIP = 0       # /dev/gpiochip0

# -----------------------------
# Tare parameters
# -----------------------------
TARE_SAMPLES = 20
SAMPLE_DELAY_SEC = 0.05
BATCH_DELAY_SEC = 0.5
ROLLING_WINDOW_SIZE = 5


def hx711_read_raw(handle):
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


def tare_load_cell(handle, samples=TARE_SAMPLES, sample_delay=SAMPLE_DELAY_SEC):
    readings = []

    for _ in range(max(1, int(samples))):
        raw_val = hx711_read_raw(handle)
        readings.append(raw_val)
        time.sleep(max(0.0, float(sample_delay)))

    offset = sum(readings) / len(readings)
    return offset, readings


def format_delta(current, previous):
    if previous is None:
        return "n/a"
    return f"{current - previous:+.2f}"


def main():
    handle = lgpio.gpiochip_open(CHIP)
    lgpio.gpio_claim_input(handle, DOUT_PIN)
    lgpio.gpio_claim_output(handle, SCK_PIN, 0)

    try:
        print("Remove all weight from the load cell before taring.")
        print("Capturing baseline samples continuously. Press Ctrl+C to stop.")

        batch_offsets = []
        previous_offset = None
        batch_index = 0

        while True:
            batch_index += 1
            offset, readings = tare_load_cell(handle)
            batch_offsets.append(offset)

            rolling_window = batch_offsets[-ROLLING_WINDOW_SIZE:]
            rolling_average = sum(rolling_window) / len(rolling_window)

            print(
                f"Batch {batch_index:03d}: offset={offset:.2f} | "
                f"delta={format_delta(offset, previous_offset)} | "
                f"rolling_avg({len(rolling_window)})={rolling_average:.2f} | "
                f"samples={len(readings)}"
            )

            previous_offset = offset
            time.sleep(max(0.0, float(BATCH_DELAY_SEC)))
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        lgpio.gpiochip_close(handle)
        print("Clean exit.")


if __name__ == "__main__":
    main()