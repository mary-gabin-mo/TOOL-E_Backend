"""
PURPOSE:
Standalone Picamera2 single-image capture helper used by hardware test scripts.

RUNTIME ROLE:
- Developer utility module; not imported by kiosk runtime app.

API ENDPOINTS USED:
- None.
"""

from picamera2 import Picamera2
from datetime import datetime
import time
import os
from PIL import Image, ImageOps

# -----------------------------
# Resize image function
# -----------------------------
def resize_and_pad_pil(image_path, target_size, pad_color="white"):
    """
    Open an image, resize it to a square with padding, and return the PIL image.
    """
    img = Image.open(image_path)

    new_img = ImageOps.pad(
        img,
        (target_size, target_size),
        method=Image.LANCZOS,
        color=pad_color,
        centering=(0.5, 0.5),
    )

    return new_img


# -----------------------------
# Paths / globals
# -----------------------------
SAVE_DIR = os.path.expanduser("~/Desktop/tool_photos")
os.makedirs(SAVE_DIR, exist_ok=True)

picam2 = None  # Global camera instance


# -----------------------------
# Camera control functions
# -----------------------------
def init_camera():
    """Initialize the camera once and start it."""
    global picam2
    if picam2 is not None:
        return  # already initialized

    picam2 = Picamera2()
    config = picam2.create_still_configuration()
    picam2.configure(config)

    print("Starting camera...")
    picam2.start()
    time.sleep(1)  # short warm-up


def take_picture():
    """
    Capture one photo, resize + pad it for object detection,
    save it to disk, and return the filepath.
    """
    if picam2 is None:
        init_camera()

    # Generate a timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(SAVE_DIR, f"photo_{timestamp}.jpg")

    print("Capturing one photo...")
    picam2.capture_file(filename)
    print(f"Saved raw image to: {filename}")

    # Process: resize + pad to 384x384 with white background
    processed_img = resize_and_pad_pil(filename, 384, pad_color="white")
    processed_img.save(filename, quality=95)

    print(f"Resized and saved to: {filename}")
    return filename


def close_camera():
    """Stop and close the camera safely."""
    global picam2
    if picam2 is not None:
        picam2.stop()
        picam2.close()
        picam2 = None
        print("Camera closed.")


# -----------------------------
#run behaviours

if __name__ == "__main__":
    init_camera()
    take_picture()
    close_camera()
