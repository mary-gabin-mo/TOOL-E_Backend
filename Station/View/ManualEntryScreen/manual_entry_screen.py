"""
PURPOSE:
Allows manual user-ID entry when card scanning is unavailable.

RUNTIME ROLE:
- Captures typed ID, validates user via API workflow, and routes into action flow.

API ENDPOINTS USED:
- POST /validate_user (indirectly via `APIClient`).
"""

from View.baseScreen import BaseScreen
from kivy.app import App
from kivy.core.window import Window
import time

import threading
from kivy.clock import mainthread

class ManualEntryScreen(BaseScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Aggressive debouncing for touchscreen - Pi is slow
        self._last_input_time = 0
        self._debounce_delay = 0.15  # 350ms debounce for Pi touchscreen
        self._is_submitting = False

    def _on_ucid_text_change(self, text):
        """Handle text input changes and update button enabled state"""
        # Limit to 8 digits
        if len(text) > 8:
            self.ids.ucid_input.text = text[:8]
        # Enable ENTER button only when exactly 8 digits are entered
        self.ids.enter_btn.disabled = len(self.ids.ucid_input.text) != 8

    def on_enter(self, *args):
        super().on_enter(*args)
        self._is_submitting = False
        self.set_loading_state(False)
        Window.bind(on_key_down=self._on_keyboard_down)

    def on_leave(self, *args):
        Window.unbind(on_key_down=self._on_keyboard_down)
        self.clear_input(bypass_debounce=True)
        super().on_leave(*args)

    def _on_keyboard_down(self, instance, keyboard, keycode, text, modifiers):
        """Handle hardware keyboard input (e.g. barcode scanner)"""
        # Handle Enter key (13 or 'enter')
        if keyboard == 13 or text == '\r':
            self.submit_ucid()
            return True
        
        # Handle Backspace (8)
        if keyboard == 8:
            self.delete_last(bypass_debounce=True)
            return True
            
        # Handle Numbers
        if text and text.isdigit():
            self.add_digit(text, bypass_debounce=True)
            return True
            
        return False

    def _check_debounce(self):
        """Check if enough time has passed since last input"""
        current_time = time.time()
        if current_time - self._last_input_time >= self._debounce_delay:
            self._last_input_time = current_time
            return True
        return False

    def add_digit(self, digit, bypass_debounce=False):
        """Add a digit to the input with debouncing"""
        if self._is_submitting:
            return
        if not bypass_debounce and not self._check_debounce():
            return
        
        # Limit length to avoid infinite strings
        current_text = self.ids.ucid_input.text
        if len(current_text) < 8: 
            self.ids.ucid_input.text += digit
            print(f"[INPUT] Added digit: {digit}")

    def clear_input(self, bypass_debounce=False):
        """Clear all input"""
        if self._is_submitting:
            return
        if not bypass_debounce and not self._check_debounce():
            return
        self.ids.ucid_input.text = ""
        print("[INPUT] Cleared input")

    def delete_last(self, bypass_debounce=False):
        """Remove the last character from the UCID input."""
        if self._is_submitting:
            return
        if not bypass_debounce and not self._check_debounce():
            return
        current_text = self.ids.ucid_input.text
        if len(current_text) > 0:
            self.ids.ucid_input.text = current_text[:-1]
            print(f"[INPUT] Deleted character, now: {self.ids.ucid_input.text}")

    def submit_ucid(self):
        if self._is_submitting:
            return

        ucid = self.ids.ucid_input.text
        if not ucid:
            return

        print(f"Submitting UCID: {ucid}")
        
        self._is_submitting = True
        self.set_loading_state(True)
        
        # Run API in thread to prevent UI freezing
        threading.Thread(target=self._submit_ucid_thread, args=(ucid,)).start()

    @mainthread
    def set_loading_state(self, is_loading):
        self.ids.ucid_input.disabled = is_loading
        self.ids.numpad_grid.disabled = is_loading
        self.ids.controls_box.disabled = is_loading
        self.ids.input_box.opacity = 0 if is_loading else 1
        self.ids.loading_box.opacity = 1 if is_loading else 0
        self.ids.loading_box.height = '110dp' if is_loading else '0dp'

    def _submit_ucid_thread(self, ucid):
        app = App.get_running_app()
        try:
            result = app.api_client.validate_user(ucid)
        except Exception as e:
            print(f"[UI] Manual validation failed: {e}")
            result = {'success': False, 'error': 'Authorization failed. Please try again.'}
        self._handle_validation_result(result)

    @mainthread
    def _handle_validation_result(self, result):
        self._is_submitting = False
        self.set_loading_state(False)
        app = App.get_running_app()
        
        if result['success'] == True:
            # Save the user info to the session once validated
            app.session.user_data = result['user']
            # Save the specific ID (mapping API 'ucid' to session 'user_id')
            app.session.user_id = str(result['user'].get('ucid', ''))
            self.go_to('action selection screen')
            
        else:
            # if the validation failed, show the appropriate error message
            error_screen = self.manager.get_screen('user error screen')
            error_screen.set_error_message(result['error'])
            self.go_to('user error screen')
