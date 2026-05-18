# TOOL-E Kiosk GUI

### Installing pyscard on Raspberry Pi OS (Debian/Ubuntu) you can do this once:
```
sudo apt update
sudo apt install \
        build-essential        \
        python3-dev            \   # match whatever Python you’re using (python3.12-dev etc.)
        swig                   \
        libpcsclite-dev        \   # PC/SC headers
        pcscd                  \   # optional, daemon to talk to readers
        libusb-1.0-0-dev       # if you use USB readers

# Then install pyscard in your venv
pip install pyscard
```

### Installing picamera2
```
# make sure the low‑level camera stack is available from the OS
sudo apt update
sudo apt install \
        libcamera-apps libcamera-dev \   # runtime + headers
        libv4l-dev          \             # V4L compatibility (used by picamera2)
        python3-picamera2      # optional – pre‑built wheel for the wrapper

# (in case you also build other extensions such as python-prctl)
sudo apt install build-essential python3-dev \
                                 swig libcap-dev

# now install the Python package; if you installed python3-picamera2
# above you can skip this step, otherwise build from pip:
python -m pip install --upgrade pip setuptools wheel
pip install picamera2
```

> **Note:** there is *no* package called `libcamera0` on recent Pi OS versions –
> the library is provided by `libcamera-apps`/`libcamera-dev`.
>
> **If you see a Python error like `No module named libcamera` when launching
> the app, it means the *Python bindings* for libcamera are missing.**
> Those are supplied by the `python3-libcamera` package (or can be pulled in
> automatically by installing `python3-picamera2`), not by `picamera2` itself.
> Install them with:
>
> ```bash
> sudo apt install python3-libcamera
> ```
>
> and make sure the interpreter running the kiosk has access to system
> site‑packages.  If you use a virtualenv, create it with:
>
> ```bash
> python3 -m venv --system-site-packages station-venv
> source station-venv/bin/activate
> pip install -r requirements_pi.txt
> ```
>
> or add `/usr/lib/python3/dist-packages` to the venv’s `PYTHONPATH`.  Once
> the bindings are visible the import error will disappear.

This extra step is often overlooked on a freshly imaged SD card; without
it `picamera2` will fail because it tries to `import libcamera` internally.
Once the bindings are installed the import error should disappear.

---

## TOOL-E Station (Full README)

Raspberry Pi kiosk client for TOOL-E. This service runs on the station hardware (Raspberry Pi) and handles kiosk UI, hardware I/O (card reader, lights, sensors), image capture for ML identification, and communication with the central Server API.

### Overview

- Purpose: Run a lightweight kiosk on-site to perform tool checkouts/returns and capture images for ML identification.
- Language: Python 3.10+ (designed to run on Raspberry Pi OS / Debian)
- Entrypoint: `main.py`

### Project Structure

- `main.py`: Station app bootstrap and main loop.
- `config.py`: Station configuration and environment reading.
- `services/`: Station services and helpers.
    - `api_client.py`: HTTP client for Server endpoints.
    - `hardware.py`: Abstraction over GPIO/serial hardware used by the kiosk.
    - `session.py`: Station session management and local caching.
    - `hardware scripts/`: Small standalone scripts for testing hardware components (lights, sensors, camera capture, reader). Examples:
        - `lights.py`
        - `sensors.py`
        - `single_capt.py`
        - `test_reader.py`
- `assets/`: Local images and static assets used by the kiosk UI.
- `View/`: Kivy-based UI layer for the kiosk application.
    - `baseScreen.py` / `baseScreen.kv`: Base class for all screens; handles common screen lifecycle and styling.
    - `screens.py`: Screen manager and navigation orchestration.
    - Screen folders (each contains a `.py` and `.kv` file):
        - `WelcomeScreen/`: Welcome/login entry point.
        - `UserErrorScreen/`: Error/exception display.
        - `ToolSelectionScreen/`: Tool inventory browser or search interface.
        - `ToolConfirmScreen/`: Confirmation screen for selected tool.
        - `CaptureScreen/`: Camera/image capture interface for ML identification.
        - `ActionSelectionScreen/`: User chooses checkout/return action.
        - `ManualEntryScreen/`: Manual/text-based tool entry.
        - `ManualToolEntryScreen/`: Manual tool data confirmation.
        - `CheckoutConfirmationScreen/`: Checkout transaction confirmation.
        - `ToolReturnSelectionScreen/`: Select tool to return.
        - `ReturnConfirmationScreen/`: Return transaction confirmation.
        - `TransactionConfirmScreen/`: Final transaction display/receipt.
    - `components/`: Reusable UI components.
        - `user_info_footer.py` / `user_info_footer.kv`: Footer widget showing user info.
    - `widgets/`: Custom widget implementations.
        - `calendar_popup.py`: Calendar/date picker widget.
    - `FOOTER_TEMPLATE.txt`: Footer layout template.

### Prerequisites

- TOOL-E Kiosk Hardware
    - Raspberry Pi (Pi 3/4 or newer) or compatible Debian-based device
    - Python 3.10+ installed
    - Camera module
    - Hardware peripherals (card reader, LEDs, load cell sensors)

### Installation

1. On the station device, create and activate a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install station-specific dependencies:

```bash
pip install -r requirements_pi.txt
```

3. Configure the station by editing `config.py` or creating environment variables used by the module (see next section).

### Environment & Configuration

The station reads configuration from `config.py`. Key environment variables:

**Network:**
- `SERVER_IP`: IP address of the central Server (default: `127.0.0.1`)
- `SERVER_PORT`: Server port (default: `5000`)
- `NETWORK_TIMEOUT`: API request timeout in seconds (default: `5.0`)

**Hardware (GPIO/Pins):**
- `PIN_LOAD_CELL_DAT`, `PIN_LOAD_CELL_CLK`: Load cell data/clock pins
- `PIN_LED_GREEN`, `PIN_LED_RED`, `PIN_LED_YELLOW`: LED control pins
- `PIN_BUZZER`: Buzzer control pin
- `LOAD_CELL_THRESHOLD`: Minimum weight to trigger detection (default: `2000.0`)
- `LOAD_CELL_DEBOUNCE`: Debounce time in seconds (default: `2.0`)
- `AUTO_TARE_ENABLED`: Enable automatic tare (calibration) (default: `true`)
- `AUTO_TARE_INTERVAL_SEC`: Tare check interval (default: `300`)
- `CARD_READER_POWER_ON_CMD`, `CARD_READER_POWER_OFF_CMD`: Optional USB reader power control commands

**UI:**
- `ASSETS_DIR`: Path to assets folder (automatically resolved)
- `LOGO_PATH`: Path to logo image

Edit `.env` or `config.py` to override defaults locally. Load with `dotenv` for environment-specific setup on the Pi.

### Running the Station

Start the kiosk app on the device:

```bash
cd Desktop/kiosk/TOOL-E/Station
source st_venv/bin/activate
python main.py
```

For kiosk deployments you may want to run it under a process manager (systemd) so it starts on boot.

### Hardware & Camera

- The `hardware.py` module encapsulates GPIO and serial interactions. Adapt pins and device paths there to match your hardware.
- Use the scripts in `hardware scripts/` to test individual components before running the full kiosk.
- Camera capture utilities are provided in `hardware scripts/single_capt.py` and integrated into `services` for uploads.

### Kivy UI Layer

The kiosk UI is built with **Kivy** and organized as a multi-screen application:

- **Screen Architecture**: Each page of the app is a separate `Screen` subclass residing in `View/{ScreenName}/`.
- **Base Class**: All screens inherit from `baseScreen.py`, which provides common functionality (lifecycle hooks, styling, navigation).
- **Navigation**: The `screens.py` module manages transitions between screens using Kivy's `ScreenManager`.
- **Layout Files**: Each screen has a corresponding `.kv` file (Kivy markup language) defining the visual layout.
- **Components**: Reusable UI widgets are in `View/components/` and `View/widgets/` (e.g., footer, calendar picker).
- **Styling**: Common styles, colors, and themes should be applied consistently via the base screen or a shared theme file.

Typical user flow:
1. **WelcomeScreen** → User logs in with card or chooses to enter UCID manually
2. **ActionSelectionScreen** → User picks checkout or return
3. **CaptureScreen** → Camera captures tool image for ML identification
4. **ToolConfirmScreen** → User confirms if the ML recognized the tool correctly
5. **ToolSelectionScreen** → If ML recognition was incorrect, user selects the correct tool name from the list
6. **TransactionConfirmScreen** → User selects return date and purpose of checkout, then confirms transaction
7. **CheckoutConfirmationScreen** / **ReturnConfirmationScreen** → Final receipt/confirmation display with borrowed items or returned item name

Authentication error states route to **UserErrorScreen**, and **ManualEntryScreen** allows fallback UCID input.

### Networking & API

- The station communicates with the Server API for user validation, transaction creation, and ML identification (`/identify_tool`, `/transactions/kiosk`, etc.).
- The `services/api_client.py` centralizes HTTP calls and retries. Ensure `SERVER_URL` points at your Server instance.

### Development & Debugging

- Use the lightweight hardware test scripts to validate peripheral wiring.
- Logs print to stdout; for long-term deployments run under `systemd` or another supervisor and capture logs with `journalctl` or your logging stack.


### Notes

- `requirements_pi.txt` lists Pi-specific dependencies; keep it in sync with the station runtime.
- Adjust camera and reader timeouts in `config.py` to match your hardware's responsiveness.
- If the station must operate offline briefly, consider local retry/backoff logic in `api_client.py` and queue transactions to upload when connectivity returns.

### Useful Commands

- Create venv and install: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements_pi.txt`