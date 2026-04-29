"""
PURPOSE:
Hardware abstraction/service for kiosk peripherals (load cell, LEDs, buzzer,
card reader, and Pi-specific GPIO behavior).

RUNTIME ROLE:
- Dispatches app events: `on_load_cell_detect`, `on_card_scanned`.
- Encapsulates Pi hardware polling and mock behavior for non-Pi development.

API ENDPOINTS USED:
- None directly.
"""

import platform
import traceback
import subprocess
from kivy.app import App
from kivy.event import EventDispatcher
from smartcard.System import readers
from smartcard.util import toHexString
from kivy.clock import Clock
from kivy.core.window import Window

# Import settings from your config.py
from config import (
    PIN_LOAD_CELL_DAT, PIN_LOAD_CELL_CLK,
    PIN_LED_GREEN, PIN_LED_RED, PIN_LED_YELLOW,
    PIN_BUZZER,
    LOAD_CELL_THRESHOLD,
    LOAD_CELL_RETRIGGER_COOLDOWN_SEC,
    CARD_READER_POWER_ON_CMD,
    CARD_READER_POWER_OFF_CMD,
)

# Check system type
IS_PI = platform.machine() in ("aarch64", "armv7l")

class HardwareManager(EventDispatcher):
    """
    The central hub for all hardware interactions.
    Dispatches events that Screens can listen to.
    """
    
    # Define custome events that the UI can listen for
    __events__ = ('on_load_cell_detect', 'on_card_scanned')
    
    def __init__(self, **kwargs):
        super().__init__(*kwargs)
        self.is_pi = IS_PI
        self._pcsc_poll_event = None
        self._led_state = None
        
        # Load Cell State
        self.lgpio_handle = None
        self.stable_reads = 0
        self.offset = 499750 # weight of the bed in raw number
        # OPTIMIZATION: Adjusted stable reads for lower polling frequency
        # At 5Hz (0.2s), 2 reads = ~0.4s debounce (was 3 reads @ 10Hz = ~0.3s)
        self.STABLE_READS_REQUIRED = 2
        self.POLL_INTERVAL_SEC = 0.2
        self.RETRIGGER_COOLDOWN_POLLS = max(self.STABLE_READS_REQUIRED, int(round(LOAD_CELL_RETRIGGER_COOLDOWN_SEC / self.POLL_INTERVAL_SEC)))
        self.RETRIGGER_DELAY_POLLS = self.RETRIGGER_COOLDOWN_POLLS - self.STABLE_READS_REQUIRED
        self.poll_counter = 0  # For periodic debug output
        
        if self.is_pi:
            self._setup_real_hardware()
        else:
            self._setup_mock_hardware()
            
    # --- Event Stubs (required by Kivy) ---
    def on_load_cell_detect(self, weight):
        """Called when load cell detects an object > threshold"""
        pass
    
    def on_card_scanned(self, card_id):
        """Called when a UNICARD is tapped"""
        pass
    
    # --- REAL HARDWARE (Raspberry Pi) ---
    def _setup_real_hardware(self):
        print("[HARDWARE] Initializing Real Pi Hardware (LGPIO)...")
        
        try:
            import lgpio
            
            # 1. Open GPIO Chip (usually 0 on Pi 5)
            self.lgpio_handle = lgpio.gpiochip_open(0)
            
            # 2. Setup Load Cell Pins
            lgpio.gpio_claim_input(self.lgpio_handle, PIN_LOAD_CELL_DAT)
            lgpio.gpio_claim_output(self.lgpio_handle, PIN_LOAD_CELL_CLK, 0)
            
            # 3. Setup LEDs (Claiming them for output)
            lgpio.gpio_claim_output(self.lgpio_handle, PIN_LED_GREEN, 0)
            lgpio.gpio_claim_output(self.lgpio_handle, PIN_LED_RED, 0)
            lgpio.gpio_claim_output(self.lgpio_handle, PIN_LED_YELLOW, 0)
            
            # 3b. Setup Buzzer (Claiming it for output)
            lgpio.gpio_claim_output(self.lgpio_handle, PIN_BUZZER, 0)

            self.set_led_state('idle')
            print("[HARDWARE] LEDs configured. Idle LED state applied.")

            # 4. Start polling the load cell 
            # OPTIMIZATION: Reduce polling frequency from 10Hz (0.1s) to 5Hz (0.2s)
            # This keeps responsiveness while cutting CPU usage in half
            print("[HARDWARE] Starting load cell polling (0.2s interval - optimized)...")
            Clock.schedule_interval(self._poll_load_cell, self.POLL_INTERVAL_SEC)
            print("[HARDWARE] Load cell polling scheduled successfully!")

        except ImportError:
            print("[ERROR] lgpio not found. Hardware control disabled.")
            self.lgpio_handle = None
        except Exception as e:
            print(f"[ERROR] GPIO Setup failed: {e}")
            print(f"[ERROR] Full traceback: ", exc_info=True)
            self.lgpio_handle = None
        
        # implement GPIO setup...
        # implement other methods for the real hardware
        barcode = "#barcode_test#" ### Replace with the card reader input
        self.dispatch('on_card_scanned', barcode)
        
        # Card reader polling is controlled by screen lifecycle.

    def start_card_reader_polling(self):
        """Start PC/SC card polling loop if not already running."""
        self._set_card_reader_power(True)
        if self._pcsc_poll_event is None:
            print("[HARDWARE] Starting PC/SC Reader Polling...")
            self._pcsc_poll_event = Clock.schedule_interval(self._check_pcsc_reader, 0.5)

    def stop_card_reader_polling(self):
        """Stop PC/SC card polling loop if running."""
        if self._pcsc_poll_event is not None:
            self._pcsc_poll_event.cancel()
            self._pcsc_poll_event = None
            print("[HARDWARE] Stopped PC/SC Reader Polling.")
        self._set_card_reader_power(False)

    def _set_card_reader_power(self, enabled):
        """
        Optional USB power control for the card reader device.
        Set CARD_READER_POWER_ON_CMD / CARD_READER_POWER_OFF_CMD in config/.env.
        """
        cmd = CARD_READER_POWER_ON_CMD if enabled else CARD_READER_POWER_OFF_CMD
        if not cmd:
            return

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                print(f"[HARDWARE] Card reader power command failed ({result.returncode}): {stderr}")
            else:
                state = "ON" if enabled else "OFF"
                print(f"[HARDWARE] Card reader USB power set {state}.")
        except Exception as e:
            print(f"[HARDWARE] Card reader power command error: {e}")
        
    def _read_hx711_raw(self):
        """
        Bit-banging logic to read from HX711 using lgpio.
        Ported from your provided script.
        """
        import lgpio
        import time
        
        # Wait for DOUT to go low (ready)
        # Timeout loop to prevent UI freezing if sensor is disconnected
        timeout = 0
        while lgpio.gpio_read(self.lgpio_handle, PIN_LOAD_CELL_DAT) == 1:
            time.sleep(0.0001)
            timeout += 1
            if timeout > 1000: # approx 0.1s timeout
                return None

        value = 0
        # Pulse clock 24 times to read data
        for _ in range(24):
            lgpio.gpio_write(self.lgpio_handle, PIN_LOAD_CELL_CLK, 1)
            value = (value << 1) | lgpio.gpio_read(self.lgpio_handle, PIN_LOAD_CELL_DAT)
            lgpio.gpio_write(self.lgpio_handle, PIN_LOAD_CELL_CLK, 0)

        # Pulse clock 1 more time to set gain to 128 (standard)
        lgpio.gpio_write(self.lgpio_handle, PIN_LOAD_CELL_CLK, 1)
        lgpio.gpio_write(self.lgpio_handle, PIN_LOAD_CELL_CLK, 0)

        # Convert 24-bit 2's complement to signed int
        if value & 0x800000:
            value -= 1 << 24

        return value    
    
    def _poll_load_cell(self, dt):
        """
        Periodically checks weight. Replaces 'wait_for_object' loop.
        """
        self.poll_counter += 1
        
        if not self.lgpio_handle:
            if self.poll_counter % 50 == 0:  # Print every 5 seconds (50 polls * 0.1s)
                print("[HARDWARE] Waiting for lgpio handle...")
            return

        raw_val = self._read_hx711_raw()
        if raw_val is None:
            if self.poll_counter % 50 == 0:
                print("[HARDWARE] Load cell sensor not responding")
            return # Sensor not ready

        current_weight = (raw_val - self.offset)
        
        # # Print status every 10 polls (1 second)
        # if self.poll_counter % 10 == 0:
        #     print(f"[LOADCELL] Raw: {raw_val}, Weight: {current_weight:.1f}g, Threshold: {LOAD_CELL_THRESHOLD}g, Stable: {self.stable_reads}/{self.STABLE_READS_REQUIRED}")

        # Check Threshold
        if current_weight > LOAD_CELL_THRESHOLD:
            self.stable_reads += 1
        else:
            self.stable_reads = 0

        # Trigger Event
        if self.stable_reads >= self.STABLE_READS_REQUIRED:
            print(f"\n{'='*60}")
            print(f"[HARDWARE] **OBJECT DETECTED!**")
            print(f"[HARDWARE] Weight: {(current_weight/377):.1f}g (raw: {raw_val})")
            print(f"[HARDWARE] Dispatching on_load_cell_detect event...")
            print(f"{'='*60}\n")
            self.dispatch('on_load_cell_detect', current_weight)
            # Reset stable reads so we don't trigger 30 times a second while object sits there
            # Or you can add logic to wait for removal before triggering again.
            self.stable_reads = -self.RETRIGGER_DELAY_POLLS
        
    def _check_pcsc_reader(self, dt):
        # Hard safety guard: only read cards while welcome screen is active.
        app = App.get_running_app()
        if not app or not getattr(app, 'manager_screens', None):
            return
        if app.manager_screens.current != 'welcome screen':
            return

        try:
            # Get list of available readers
            r_list = readers()
            if not r_list:
                return # No reader plugged in
            
            reader = r_list[0] # Use the first reader found
            # print(f"Using: {reader=}")        # DEBUG
            connection = reader.createConnection()
            
            # Try to connect (fails if no card is on the reader)
            try:
                connection.connect()
                
                # Send ADPU command to get the UID (Standard for Mifare cards)
                # Command: FF CA 00 00 00 (Get Data)
                GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                data, sw1, sw2 = connection.transmit(GET_UID)
                
                if sw1 == 0x90: # Success code
                    # Convert raw bytes to a hex string (e.g., "04 A3 5E...")
                    uid_hex = toHexString(data).replace(" ", "")
                    print(f"[HARDWARE] PC/SC Card Detected: {uid_hex}")
                    
                    # Dispatch event
                    self.dispatch('on_card_scanned', uid_hex)
            except Exception:
                # No card present, just ignore
                # print("no card detected")     # DEBUG
                pass
        
        except Exception as e:
            print(f"Error polling reader: {e}")
            
    def cleanup(self):
        """Release GPIO resources on app exit."""
        self.stop_card_reader_polling()
        if self.lgpio_handle is not None:
            import lgpio
            self._set_all_leds_off()
            lgpio.gpiochip_close(self.lgpio_handle)
            self.lgpio_handle = None
            print("[HARDWARE] GPIO handle closed.")

    def _set_all_leds_off(self):
        """Turn all LEDs off (active-low wiring)."""
        if not self.is_pi or self.lgpio_handle is None:
            return

        import lgpio
        lgpio.gpio_write(self.lgpio_handle, PIN_LED_GREEN, 1)
        lgpio.gpio_write(self.lgpio_handle, PIN_LED_YELLOW, 1)
        lgpio.gpio_write(self.lgpio_handle, PIN_LED_RED, 1)
        lgpio.gpio_write(self.lgpio_handle, PIN_BUZZER, 1)

    def set_led_state(self, state):
        """
        Set kiosk status LED state.
        Supported states:
        - idle: green
        - transaction: yellow
        - alert: red
        """
        if not self.is_pi or self.lgpio_handle is None:
            self._led_state = state
            return

        state = (state or '').strip().lower()
        pin_map = {
            'idle': PIN_LED_GREEN,
            'transaction': PIN_LED_YELLOW,
            'alert': PIN_LED_RED,
        }

        target_pin = pin_map.get(state)
        if target_pin is None:
            print(f"[HARDWARE] Unknown LED state requested: {state}")
            return

        import lgpio
        self._set_all_leds_off()
        # Active-low LED wiring: 0 = on, 1 = off
        lgpio.gpio_write(self.lgpio_handle, target_pin, 0)
        self._led_state = state

        # Buzz buzzer when alert state is triggered
        if state == 'alert':
            self.buzz()

    def buzz(self):
        """Trigger a buzzer beep pattern (two short beeps)."""
        if not self.is_pi or self.lgpio_handle is None:
            return

        import lgpio
        import time
        import threading

        def _buzz_thread():
            try:
                # Active-low buzzer: 0 = on, 1 = off
                for _ in range(2):
                    lgpio.gpio_write(self.lgpio_handle, PIN_BUZZER, 0)
                    time.sleep(0.2)
                    lgpio.gpio_write(self.lgpio_handle, PIN_BUZZER, 1)
                    time.sleep(0.1)
            except Exception as e:
                print(f"[HARDWARE] Buzzer error: {e}")

        # Run in background thread so we don't block the main thread
        threading.Thread(target=_buzz_thread, daemon=True).start()
    
    # --- MOCK HARDWARE (Mac/Windows) ---
    def _setup_mock_hardware(self):
        print("[HARDWARE] Initializing MOCK Hardware (Dev Mode)...")
        print("   -> Press 'd' to simulate Load Cell Trigger")
        print("   -> Press 'c' to simulate Card Scan")
        
        # Bind keyboard keys to simulate hardware events
        Window.bind(on_key_down=self._on_mock_keyboard_input)
        
    def _on_mock_keyboard_input(self, window, key, scancode, codepoint, modifiers):
        # 'd' key (100) simulates Load Cell
        if key == 100: 
            print("[MOCK] Load Cell Triggered!")
            self.dispatch('on_load_cell_detect', weight=500.0)
        
        # 'c' key (99) simulates Card Tap
        elif key == 99: 
            print("[MOCK] Card Scanned!")
            self.dispatch('on_card_scanned', "10131867")
                
