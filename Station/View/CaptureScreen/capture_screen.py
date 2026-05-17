"""
PURPOSE:
Captures tool image (camera), stores local transaction image metadata, and
submits image for ML identification.

RUNTIME ROLE:
- Entry point for image-based tool recognition in both borrow and return flows.
- Persists capture info into session for downstream screens.

API ENDPOINTS USED:
- POST /identify_tool (via `APIClient.upload_tool_image`).
"""

import cv2
import platform
import os
import threading
import logging
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.graphics.texture import Texture

from View.baseScreen import BaseScreen
from PIL import Image, ImageOps

# Suppress debug logging from picamera2 and other libraries
logging.getLogger('picamera2').setLevel(logging.WARNING)
logging.getLogger('libcamera').setLevel(logging.WARNING)
logging.getLogger('picamera2.job').setLevel(logging.WARNING)

# Detect if we are on the Pi
IS_RASPBERRY_PI = platform.machine() in ("aarch64", "armv7l")


class CaptureScreen(BaseScreen):

    capture = None  # For OpenCV (laptop)
    picam2 = None   # For Picamera2 (Pi)
    update_event = None

    _pending_capture_event = None
    _is_capturing = False
    _pending_weight_grams = 0
    _camera_init_timeout_event = None
    _camera_ready_reported = False

    def on_enter(self):
        """
        Called when this screen is displayed.
        Starts listening to hardware events.
        """
        print("[DEBUG] CaptureScreen: on_enter called")

        self._is_capturing = False
        self._pending_weight_grams = 0
        self._camera_ready_reported = False
        if self._pending_capture_event:
            self._pending_capture_event.cancel()
            self._pending_capture_event = None
        if self._camera_init_timeout_event:
            self._camera_init_timeout_event.cancel()
            self._camera_init_timeout_event = None

        # 1. Reset UI to "Initializing" state
        self.set_processing_mode(True, message="Initializing Camera...")

        # 2. Bind hardware events
        app = App.get_running_app()
        if hasattr(app, 'hardware'):
            if hasattr(app.hardware, 'set_led_state'):
                app.hardware.set_led_state('transaction')
            if hasattr(app.hardware, 'reset_load_cell_detection_state'):
                app.hardware.reset_load_cell_detection_state(armed=False)
            print("[DEBUG] Binding on_load_cell_detect")
            try:
                app.hardware.unbind(on_load_cell_detect=self.handle_load_cell_trigger)
            except Exception:
                pass
            app.hardware.bind(on_load_cell_detect=self.handle_load_cell_trigger)

            if hasattr(app.hardware, 'tare_load_cell'):
                print("[DEBUG] Starting load cell tare")
                threading.Thread(target=app.hardware.tare_load_cell, daemon=True).start()

        # 3. Start camera in background
        # Guard against camera drivers hanging forever when hardware is missing.
        self._camera_init_timeout_event = Clock.schedule_once(self._on_camera_init_timeout, 8)
        threading.Thread(target=self._init_camera_async, daemon=True).start()

    @mainthread
    def _on_camera_init_timeout(self, dt):
        if self._camera_ready_reported:
            return
        print("[ERROR] Camera init timed out")
        self._camera_ready_reported = True
        self.set_processing_mode(True, message="Camera Error!\nCheck camera/power")

    def _init_camera_async(self):
        """Background init to prevent UI freeze."""
        print(f"[DEBUG] Initializing Camera (Pi Mode: {IS_RASPBERRY_PI})")
        success = False

        try:
            if IS_RASPBERRY_PI:
                from picamera2 import Picamera2
                self.picam2 = Picamera2()
                config = self.picam2.create_still_configuration(
                    main={"size": (1280, 720), "format": "RGB888"},
                    lores={"size": (480, 360), "format": "RGB888"},
                )
                self.picam2.configure(config)
                self.picam2.start()
                success = True
            else:
                # Keep dev startup simple and deterministic.
                self.capture = cv2.VideoCapture(0)
                if self.capture and self.capture.isOpened():
                    success = True
        except Exception as e:
            print(f"[ERROR] Camera init failed: {e}")

        self._on_camera_ready(success)

    @mainthread
    def _on_camera_ready(self, success):
        """Called on Main Thread after camera init."""
        if self._camera_ready_reported:
            return

        self._camera_ready_reported = True
        if self._camera_init_timeout_event:
            self._camera_init_timeout_event.cancel()
            self._camera_init_timeout_event = None

        print(f"[DEBUG] Camera ready: success={success}")
        if success:
            self.set_processing_mode(False)
            if self.update_event:
                self.update_event.cancel()
                self.update_event = None
            self.update_event = Clock.schedule_interval(self.update_feed, 1.0 / 30.0)
            print("[DEBUG] Feed scheduled")
        else:
            self.set_processing_mode(True, message="Camera Error!")

    def on_leave(self):
        """
        Called when leaving this screen.
        Stop listening so this logic doesn't get triggered on other screens.
        """
        app = App.get_running_app()

        if hasattr(app, 'hardware'):
            try:
                app.hardware.unbind(on_load_cell_detect=self.handle_load_cell_trigger)
            except Exception:
                pass
            if hasattr(app.hardware, 'reset_load_cell_detection_state'):
                app.hardware.reset_load_cell_detection_state(armed=False)

        if self.update_event:
            self.update_event.cancel()
            self.update_event = None

        if self._pending_capture_event:
            self._pending_capture_event.cancel()
            self._pending_capture_event = None
        if self._camera_init_timeout_event:
            self._camera_init_timeout_event.cancel()
            self._camera_init_timeout_event = None

        if self.picam2:
            try:
                self.picam2.stop()
            except Exception:
                pass
            try:
                self.picam2.close()
            except Exception:
                pass
            self.picam2 = None
            print("[DEBUG] Picamera2 closed")

        if self.capture:
            self.capture.release()
            self.capture = None
            print("[DEBUG] Webcam released")

        self._is_capturing = False
        self._camera_ready_reported = False

    @mainthread
    def set_processing_mode(self, is_processing, message="Processing..."):
        """
        Toggles the UI between 'Live Feed' and 'Loading Label'.
        """
        if is_processing:
            self.ids.processing_overlay.opacity = 1
            self.ids.loading_label.text = message
            self.ids.camera_preview.opacity = 0.3
            if self.update_event:
                self.update_event.cancel()
                self.update_event = None
        else:
            self.ids.processing_overlay.opacity = 0
            self.ids.camera_preview.opacity = 1

    def update_feed(self, dt):
        """Reads a frame and updates the Kivy Image widget."""
        frame = None

        if IS_RASPBERRY_PI and self.picam2:
            try:
                frame = self.picam2.capture_array("lores")
            except Exception:
                pass
        elif self.capture:
            ret, cv_frame = self.capture.read()
            if ret:
                frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)

        if frame is None:
            return

        if not self.ids.get('camera_preview'):
            return

        if IS_RASPBERRY_PI:
            # Pi preview is mirrored; flip horizontally so left/right matches reality.
            frame = cv2.flip(frame, 1)
        else:
            frame = cv2.flip(frame, 0)
            # Rotate preview 180 degrees to match camera mounting.
            frame = cv2.rotate(frame, cv2.ROTATE_180)

        expected_size = (frame.shape[1], frame.shape[0])
        texture = self.ids.camera_preview.texture

        # Create a new texture only if it doesn't exist or size changed.
        if not texture or texture.size != expected_size:
            texture = Texture.create(size=expected_size, colorfmt='rgb')
            self.ids.camera_preview.texture = texture

        try:
            source_colorfmt = 'bgr' if IS_RASPBERRY_PI else 'rgb'
            texture.blit_buffer(frame.tobytes(), colorfmt=source_colorfmt, bufferfmt='ubyte')
            self.ids.camera_preview.canvas.ask_update()
        except Exception as e:
            print(f"[DEBUG] Texture update failed: {e}")
            
    def handle_load_cell_trigger(self, instance, weight):
        """
        Logic for when the load cell is triggered.
        Delays capture by 1.5 seconds to let object settle.
        """
        if self._is_capturing or self._pending_capture_event is not None:
            print("[DEBUG] Capture already in progress; ignoring extra trigger")
            return

        print(f"\n{'='*60}")
        print(f"[LOADCELL DETECTED] Raw Weight Value: {weight}")
        print(f"[LOADCELL DETECTED] Instance: {instance}")
        print(f"{'='*60}\n")

        # Keep a normalized grams value to attach to the next captured transaction payload.
        try:
            self._pending_weight_grams = int(round(float(weight) / 377.0))
        except Exception:
            self._pending_weight_grams = 0
        print(f"[LOADCELL DETECTED] Normalized weight for payload: {self._pending_weight_grams}g")

        print("[DEBUG] Waiting 0.6 seconds for object to settle...")
        self._pending_capture_event = Clock.schedule_once(self._delayed_capture, 0.6)

    def _delayed_capture(self, dt):
        self._pending_capture_event = None

        if self._is_capturing:
            return

        self._is_capturing = True
        print("[DEBUG] Freezing camera and capturing image...")
        self.set_processing_mode(True, message="Capturing Image...")

        # Start API upload in background
        threading.Thread(target=self.run_identification_task, daemon=True).start()

    # --- DEV - CAPTURE WITH BUTTON - REMOVE LATER ---
    def capture_btn(self, *args):
        """Dev Button: Simulate load cell trigger"""
        print("[DEV] Manual capture button pressed")
        self.handle_load_cell_trigger(None, 100.0)

    def save_current_frame(self):
        """Save high-res photo and resize using PIL logic."""
        print("[DEBUG] save_current_frame() called")
        print(f"[DEBUG] IS_RASPBERRY_PI: {IS_RASPBERRY_PI}")
        print(f"[DEBUG] self.picam2: {self.picam2}")
        print(f"[DEBUG] self.capture: {self.capture}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        milliseconds = int(datetime.now().microsecond / 1000)
        timestamp_id = f"{timestamp}-{milliseconds:03d}"

        app = App.get_running_app()
        tx_type = "BORROW"
        if hasattr(app, 'session') and getattr(app.session, 'transaction_type', None):
            tx_type = app.session.transaction_type.upper()
        filename = f"{timestamp_id}_{tx_type}.jpg"
        full_path = os.path.abspath(filename)

        success = False
        try:
            if IS_RASPBERRY_PI and self.picam2:
                self.picam2.capture_file(filename)
                print(f"[UI] Raw Pi image saved to {filename}")
                self.process_image_pil(filename)
                success = True
            elif self.capture:
                ret, frame = self.capture.read()
                if ret:
                    cv2.imwrite(filename, frame)
                    self.process_image_pil(filename)
                    success = True

            if success:
                print(f"[UI] Image saved locally: {filename}")
                if hasattr(app, 'session'):
                    app.session.start_new_transaction(
                        transaction_id=timestamp_id,
                        img_filename=full_path,
                        weight=self._pending_weight_grams,
                    )
                return full_path

        except Exception as e:
            print(f"[UI] Save Error: {e}")

        return None

    def process_image_pil(self, filepath):
        """Resize captured image for ML model input."""
        try:
            target_size = 384
            img = Image.open(filepath)
            new_img = ImageOps.pad(
                img,
                (target_size, target_size),
                method=Image.BILINEAR,
                color="white",
                centering=(0.5, 0.5),
            )
            new_img.save(filepath, quality=85, optimize=True)
            print(f"[UI] Image resized/padded to {target_size}x{target_size} with optimized quality")
        except Exception as e:
            print(f"[UI] PIL Error: {e}")

    def run_identification_task(self):
        """Background Thread: Takes photo, resizes, and uploads image to server."""
        filepath = self.save_current_frame()

        if not filepath:
            print("[ERROR] Failed to save image. Aborting API call.")
            self.handle_identification_result({'success': False, 'error': 'Failed to save image'})
            return

        print(f"[Background] Uploading {filepath}...")
        app = App.get_running_app()

        try:
            result = app.api_client.upload_tool_image(filepath)
        except Exception as e:
            result = {'success': False, 'error': str(e)}

        self.handle_identification_result(result)

    @mainthread
    def handle_identification_result(self, result):
        """Main Thread: Handle API response and navigate."""
        self._is_capturing = False
        print(f"[UI] Identification Result: {result}")

        if result and result.get('success'):
            app = App.get_running_app()
            tool_data = {}
            if hasattr(app, 'session'):
                tool_data = result.get('data', {})
                app.session.identified_tool_data = tool_data
                print(f"[DEBUG] Saved tool info to session: {tool_data}")

            prediction = tool_data.get('prediction', 'UNKNOWN')
            score = tool_data.get('score', 0)
            is_return_flow = hasattr(app, 'session') and app.session.transaction_type == "return"

            if str(prediction).upper() == 'UNKNOWN' or float(score) < 0.60:
                print(f"[UI] Low confidence ({score}) or UNKNOWN ({prediction}). Bypassing confirm screen.")
                if is_return_flow:
                    app.session.tool_was_confirmed = False
                    app.session.set_classification_correct(False)
                    self.go_to('tool return selection screen')
                else:
                    self.go_to('tool select screen')
            else:
                self.go_to('tool confirm screen')
        else:
            error_msg = result.get('error', 'Unknown Error') if result else "Connection Failed"
            print(f"[UI Error] {error_msg}")
            self.reset_feed()

    def reset_feed(self):
        self._is_capturing = False
        self.set_processing_mode(False)
        if not self.update_event:
            self.update_event = Clock.schedule_interval(self.update_feed, 1.0 / 30.0)
