"""
PURPOSE:
Standalone GPIO LED/buzzer hardware test script for Raspberry Pi.

RUNTIME ROLE:
- Developer utility only; not used by kiosk runtime.

API ENDPOINTS USED:
- None.
"""

import lgpio
import time

# GPIO pins (change if needed)
GREEN = 17
YELLOW = 22
RED = 27
BUZZER = 23

# open gpio chip
h = lgpio.gpiochip_open(0)

# setup outputs
for pin in [GREEN, YELLOW, RED, BUZZER]:
    lgpio.gpio_claim_output(h, pin)
    
def all_off():
    lgpio.gpio_write(h, GREEN, 1)
    lgpio.gpio_write(h, YELLOW, 1)
    lgpio.gpio_write(h, RED, 1)
    lgpio.gpio_write(h, BUZZER, 1)
    
def idle():
    all_off()
    lgpio.gpio_write(h, YELLOW, 0)
    
def success(): 
    all_off()
    lgpio.gpio_write(h, RED, 0)

def fail():
    all_off()
    lgpio.gpio_write(h, RED, 0)
    
    # buzzer 2 beeps
    lgpio.gpio_write(h, BUZZER, 0)
    time.sleep(0.6)
    lgpio.gpio_write(h, BUZZER, 1)
    
    
# ------------------------------------
# Example test loop
# ------------------------------------

try: 
    while True:
        idle()
        print("Idle")
        time.sleep(5)
        
        success()
        print("Success")
        time.sleep(5)

        fail()
        print("fail")
        time.sleep(5)
        
except KeyboardInterrupt:
    all_off()
    lgpio.gpiochip_close(h)
    
    