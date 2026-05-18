
"""
PURPOSE:
Landing screen that waits for card scan or manual user entry to start kiosk flow.

RUNTIME ROLE:
- Binds/unbinds card reader events.
- Validates scanned users and routes to next screen.

API ENDPOINTS USED:
- POST /validate_user (indirectly via `APIClient`).
"""

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.metrics import dp
from View.baseScreen import BaseScreen
import threading
from datetime import datetime

class WelcomeScreen(BaseScreen):
    
    def on_enter(self, *args):
        """
        Reset state when entering screen.
        """
        self.set_loading_state(False)
        
        # Reset Session Data (Safety Net)
        app = App.get_running_app()
        if hasattr(app, 'session'):
            app.session.reset()
        
        # Start listening to hardware
        if hasattr(app, 'hardware'):
            if hasattr(app.hardware, 'set_led_state'):
                app.hardware.set_led_state('idle')
            if hasattr(app.hardware, 'start_card_reader_polling'):
                app.hardware.start_card_reader_polling()
            # Bind the 'on_card_scanned' event to our function
            app.hardware.bind(on_card_scanned=self.handle_card_scan)
        
    def on_leave(self, *args):
        """
        Stop listening so this logic doesn't get triggered on other screens.
        """
        app = App.get_running_app()
        if hasattr(app, 'hardware'):
            app.hardware.unbind(on_card_scanned=self.handle_card_scan)
            if hasattr(app.hardware, 'stop_card_reader_polling'):
                app.hardware.stop_card_reader_polling()
    
    def exit_program(self):
        """
        Exit the program.
        """
        app = App.get_running_app()
        app.stop()

    def open_checkout_confirm_test(self):
        """DEV helper: navigate to checkout confirmation screen with sample data."""
        app = App.get_running_app()

        # Seed minimal sample data if not already present.
        if not getattr(app.session, 'transactions', []):
            app.session.transactions = [
                {
                    'transaction_id': 'DEV-1',
                    'tool_name': 'Sample Tool',
                }
            ]

        if not getattr(app.session, 'return_date', ''):
            app.session.return_date = datetime.now().strftime('%Y-%m-%d 23:59:59')

        self.go_to('checkout confirmation screen')
           
    @mainthread
    def set_loading_state(self, is_loading):
        """
        Toggles between the 'Instructions' and 'Loading Spinner' views.
        """       
        print(f"[UI] {is_loading=}")
        if is_loading:
            # Show Loading
            self.ids.instruction_box.opacity = 0
            self.ids.loading_box.opacity = 1
            self.ids.loading_box.height = dp(100) # Set height
            self.ids.footer_buttons.opacity = 0 # Hide buttons so user can't click twice
            self.ids.footer_buttons.disabled = True
        else:
            # Show Instructions
            self.ids.instruction_box.opacity = 1
            self.ids.loading_box.opacity = 0
            self.ids.loading_box.height = 0 # Collapse to 0 pixels
            self.ids.footer_buttons.opacity = 1 
            self.ids.footer_buttons.disabled = False
    
    @mainthread
    def handle_card_scan(self, instance, barcode):
        """
        Logic for when a card is detected.
        """
        print(f"[UI] Welcome Screen detected card: {barcode=}")
        
        # Update UI immediately
        self.set_loading_state(True)
        
        # Run the API call in a background thread so UI doens't freeze
        threading.Thread(target=self._validate_user_async, args=(barcode,)).start()
        
    def _validate_user_async(self, barcode):
        """BACKGROUND TASK: Runs in a separate thread"""
        app = App.get_running_app()
        try:
            result = app.api_client.validate_user(barcode)
        except Exception as e:
            print(f"[UI] Validation thread failed: {e}")
            result = {'success': False, 'error': 'Authorization failed. Please try again.'}
        
        # When done, pass results back to the main thread
        self._handle_validation_result(result)
        
    @mainthread
    def _handle_validation_result(self, result):
        app = App.get_running_app()
        """RESULT HANDLER: Runs back on the Main UI Thread"""
        if result['success']: # Success Logic
            # Once the user is validated, save the user info in SessionManager.
            # make sure no transaction type is pre-set
            app.session.transaction_type = ""
            app.session.user_data = result['user']
            # Save the specific ID (mapping API 'ucid' to session 'user_id')
            app.session.user_id = str(result['user'].get('ucid', ''))
            self.go_to('action selection screen')
        else: # Failure Logic
            # if the validation failed, show the appropriate error message
            error_screen = self.manager.get_screen('user error screen')
            error_screen.set_error_message(result['error'])
            self.go_to('user error screen')

    ### DEV ### 
    def submit_ucid(self):
        ucid = "10131867" # Mary's UCID for testing
        print(f"Submitting UCID: {ucid}")
        
        app = App.get_running_app()
        result = app.api_client.validate_user(ucid)
        if result['success'] == True:
            # Save the user info to the session once validated
            app.session.transaction_type = ""  # ensure fresh start
            app.session.user_data = result['user']
            # Save the specific ID (mapping API 'ucid' to session 'user_id')
            app.session.user_id = str(result['user'].get('ucid', ''))
            self.go_to('action selection screen')
            
        else:
            # if the validation failed, show the appropriate error message
            error_screen = self.manager.get_screen('user error screen')
            error_screen.set_error_message(result['error'])
            self.go_to('user error screen')
        
