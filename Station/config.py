"""
PURPOSE:
Central configuration for Station app networking, hardware pins, and UI paths.

RUNTIME ROLE:
- Defines server base URL and API endpoint constants used by `APIClient`.
- Defines GPIO pins and load-cell/card-reader behavior settings.

API ENDPOINTS DEFINED:
- /validate_user
- /identify_tool
- /transactions
- /tools
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- NETWORK SETTINGS ---
# The IP address of your FastAPI Server (PC)
# Use "localhost" for testing on Mac, or the actual IP (e.g., "192.168.1.10") for Pi
SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", 5000))

BASE_URL = f"http://{SERVER_IP}:{SERVER_PORT}"

# API Endpoints
API_VALIDATE_USER = f"{BASE_URL}/validate_user"
API_IDENTIFY_TOOL = f"{BASE_URL}/identify_tool"
API_TRANSACTION   = f"{BASE_URL}/transactions"
API_GET_TOOLS     = f"{BASE_URL}/tools"

# Timeouts (in seconds)
NETWORK_TIMEOUT = 5.0


# --- HARDWARE SETTINGS ---
# GPIO Pins (BCM Numbering)
PIN_LOAD_CELL_DAT = 5
PIN_LOAD_CELL_CLK = 6
PIN_LED_GREEN     = 17
PIN_LED_RED       = 27
PIN_LED_YELLOW    = 22
PIN_BUZZER        = 23

# Load Cell Calibration
LOAD_CELL_THRESHOLD = 2000.0  # Minimum weight (raw number) to trigger "Tool Detected"
LOAD_CELL_DEBOUNCE  = 2.0   # Seconds weight must be stable
LOAD_CELL_RETRIGGER_COOLDOWN_SEC = float(os.getenv("LOAD_CELL_RETRIGGER_COOLDOWN_SEC", "5.0"))
AUTO_TARE_ENABLED = os.getenv("AUTO_TARE_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
AUTO_TARE_INTERVAL_SEC = float(os.getenv("AUTO_TARE_INTERVAL_SEC", "300"))
AUTO_TARE_QUIET_IDLE_SEC = float(os.getenv("AUTO_TARE_QUIET_IDLE_SEC", "30"))
AUTO_TARE_SAMPLES = int(os.getenv("AUTO_TARE_SAMPLES", "20"))
AUTO_TARE_SAMPLE_DELAY_SEC = float(os.getenv("AUTO_TARE_SAMPLE_DELAY_SEC", "0.05"))

# Optional USB card-reader power control commands.
# Example with uhubctl:
# CARD_READER_POWER_OFF_CMD='sudo uhubctl -l 1-1 -p 2 -a off'
# CARD_READER_POWER_ON_CMD='sudo uhubctl -l 1-1 -p 2 -a on'
CARD_READER_POWER_ON_CMD = os.getenv("CARD_READER_POWER_ON_CMD", "").strip()
CARD_READER_POWER_OFF_CMD = os.getenv("CARD_READER_POWER_OFF_CMD", "").strip()


# --- UI SETTINGS ---
# Paths
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
LOGO_PATH  = os.path.join(ASSETS_DIR, '/images/logo_black.png')
FONT_PATH  = os.path.join(ASSETS_DIR, 'fonts')

# # Camera ##### NEED #####
# # Resolution for the "Live Feed" preview (keep low for performance)
# CAMERA_PREVIEW_RES = (640, 480)
# # Resolution for the actual recognition image (higher quality)
# CAMERA_CAPTURE_RES = (1920, 1080)