"""
PURPOSE:
Main kiosk application entrypoint. Configures runtime mode (Pi vs dev),
initializes global services, and builds/launches the full Kivy screen flow.

RUNTIME ROLE:
- Starts the app UI loop.
- Creates singleton services (`hardware`, `api_client`, `session`).
- Registers screen instances from `View/screens.py`.

API ENDPOINTS USED:
- None directly. API calls are delegated to `services/api_client.py`.
"""

import importlib
import os
import platform
import logging
# from kivy import resource_add_path

# --- Suppress library debug logging ---
logging.getLogger('picamera2').setLevel(logging.WARNING)
logging.getLogger('libcamera').setLevel(logging.WARNING)
logging.getLogger('picamera2.job').setLevel(logging.WARNING)

# --- Config - must run before other Kivy imports ---
from kivy.config import Config 
from kivy.core.window import Window

# --- PYINSTALLER ASSET FIX ---
# if hasattr(sys, '_MEIPASS'):
#     # Tell Kivy to look in the hidden pyInstaller temp folder for assets
#     resource_add_path(os.path.join(sys._MEIPASS))
#     # Also add the specific assets folder just in case
#     resource_add_path(os.path.join(sys._MEIPASS, "assets"))
# ------------------------------

IS_RASPBERRY_PI = platform.machine() in ("aarch64", "armv7l")

# Enable hot reload on Mac/Windows only
ENABLE_HOT_RELOAD = not IS_RASPBERRY_PI


if IS_RASPBERRY_PI:
    print("System: Raspberry Pi detected. Setting FULLSCREEN.")
    Config.set('graphics', 'fullscreen', 'auto')
    Config.set('graphics', 'show_cursor', '0')
    # Performance optimizations for Pi touchscreen responsiveness
    Config.set('graphics', 'multisampling', '0')  # Disable anti-aliasing
    Config.set('kivy', 'touch_log_fn', '')  # Disable touch logging overhead
    Config.set('postproc', 'enabled', '0')  # Disable post-processing

    # Enable onscreen virtual keyboard for Pi (docked inside Kivy)
    Config.set('kivy', 'keyboard_mode', 'dock')
    
    # Increase Keyboard Size
    from kivy.lang import Builder
    Builder.load_string("""
<VKeyboard>:
    # Increase height of virtual keyboard. 
    # height: dp(350)
    
    # Or use scale if you just want everything bigger
    # scale: 1.5
    
    # Simple approach: Force a larger size hint
    size_hint_y: 0.27
""")

    # Config.set('graphics', 'fullscreen', '0')
    # Config.set('graphics', 'show_cursor', '1')
    # Config.set('graphics', 'width', '800')
    # Config.set('graphics', 'height', '600')
    
    # Fix "1 finger = 2 touches" by keeping only ONE touch provider.
    # You can override at runtime: KIVY_TOUCH_PROVIDER=mtdev python3 main.py
    if not Config.has_section('input'):
        Config.add_section('input')

    Config.set('input', 'mouse', 'mouse,disable_multitouch')
    touch_provider = os.environ.get('KIVY_TOUCH_PROVIDER', 'hidinput').strip().lower()

    # Remove probe providers that can duplicate the same physical touch.
    for option in ('%(name)s', 'mtdev_%(name)s', 'hidinput_%(name)s'):
        if Config.has_option('input', option):
            Config.remove_option('input', option)

    if touch_provider == 'mtdev':
        Config.set('input', 'mtdev_%(name)s', 'probesysfs,provider=mtdev')
        print("[INPUT] Touch provider: mtdev")
    else:
        Config.set('input', 'hidinput_%(name)s', 'probesysfs,provider=hidinput')
        print("[INPUT] Touch provider: hidinput")
    
else:
    print("System: Dev Environment detected. Setting WINDOWED.")
    Config.set('graphics', 'fullscreen', '0')
    Config.set('graphics', 'width', '800')
    Config.set('graphics', 'height', '1280')
    
    Window.top = 0
    Window.left = 1400

Config.write()


# --- Local Module Imports ---
# Services 
from services.hardware import HardwareManager
from services.session import SessionManager
from services.api_client import APIClient

if ENABLE_HOT_RELOAD:
    # --- Kivy/KivyMD imports ---
    from kivymd.tools.hotreload.app import MDApp
    from kivymd.uix.screenmanager import MDScreenManager

    class KioskApp(MDApp):
        # Get the directory where this main.py file is located
        KV_DIRS = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "View")]

        def build_app(self) -> MDScreenManager:
            
            import View.screens
            
            self.title = "TOOL-E Kiosk"
            self.theme_cls.theme_style = "Light"
            self.theme_cls.primary_palette = "Red"
            
            # Initialize Services (Singleton)
            if not hasattr(self, 'hardware'):
                print("[MAIN] Creating HardwareManager...")
                self.hardware = HardwareManager()
                # Diagnostic check
                if self.hardware.lgpio_handle is not None:
                    print("[MAIN] ✓ Hardware initialized successfully with GPIO handle")
                else:
                    print("[MAIN] ✗ WARNING: Hardware initialized but GPIO handle is None!")
            if not hasattr(self, 'api_client'):
                self.api_client = APIClient()
            if not hasattr(self, 'session'):
                self.session = SessionManager()
            
            self.manager_screens = MDScreenManager()
            Window.bind(on_key_down=self.on_keyboard_down)
            importlib.reload(View.screens)
            screens = View.screens.screens
            
            for i, name_screen in enumerate(screens.keys()):
                view = screens[name_screen]["view"]()
                view.manager_screens = self.manager_screens
                view.name = name_screen
                self.manager_screens.add_widget(view)
            
            return self.manager_screens
        
        def on_keyboard_down(self, window, keyboard, keycode, text, modifiers) -> None:
            if ("meta" in modifiers or "ctrl" in modifiers) and text == "r":
                self.rebuild()
                
        def on_start(self):
            print("App Started.")
            
        def on_stop(self):
            print("App Stopping...")
            if hasattr(self, 'hardware') and IS_RASPBERRY_PI:
                try:
                    import RPi.GPIO as GPIO
                    GPIO.cleanup()
                except ImportError:
                    pass
                
else:
    # --- Kivy/KivyMD imports ---
    from kivymd.app import MDApp
    from kivymd.uix.screenmanager import MDScreenManager
    
    # Import footer component to make it available in KV files
    from View.components.user_info_footer import UserInfoFooter
    
    from View.screens import screens
    
    class KioskApp(MDApp):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.load_all_kv_files(self.directory)
            self.manager_screens = MDScreenManager()
            
        def build(self) -> MDScreenManager:
            
            self.title = "TOOL-E Kiosk"
            self.theme_cls.theme_style = "Light"
            self.theme_cls.primary_palette = "Blue"
            
            # Initialize Services (Singleton)
            if not hasattr(self, 'hardware'):
                self.hardware = HardwareManager()
            if not hasattr(self, 'api_client'):
                self.api_client = APIClient()
            if not hasattr(self, 'session'):
                self.session = SessionManager()
            
            self.generate_application_screens()
            return self.manager_screens
        
        def generate_application_screens(self) -> None:
            for i, name_screen in enumerate(screens.keys()):
                view = screens[name_screen]["view"]()
                view.manager_screens = self.manager_screens
                view.name = name_screen
                self.manager_screens.add_widget(view)
                
        def on_start(self):
            print("App Started.")
            
        def on_stop(self):
            print("App Stopping...")
            if hasattr(self, 'hardware') and IS_RASPBERRY_PI:
                try:
                    import RPi.GPIO as GPIO
                    GPIO.cleanup()
                except (ImportError, RuntimeError):
                    pass

KioskApp().run()
