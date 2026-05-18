
"""
PURPOSE:
Lets the user choose transaction mode (borrow or return) after identity is validated.

RUNTIME ROLE:
- Sets `session.transaction_type`.
- Routes user to capture flow.

API ENDPOINTS USED:
- None directly.
"""

from kivy.app import App
from kivy.clock import Clock

from View.baseScreen import BaseScreen

class ActionSelectionScreen(BaseScreen):
    
    def on_enter(self):
        """
        Reset partial transaction data if returning here.
        Does NOT clear user_data (user stays logged in).
        """
        app = App.get_running_app()
        if hasattr(app, 'hardware') and hasattr(app.hardware, 'set_led_state'):
            app.hardware.set_led_state('transaction')
        if hasattr(app, 'session'):
            app.session.transactions = []
            app.session.current_transaction = {}
            app.session.transaction_type = ""  # Reset to no action selected
            print("[UI] ActionSelection: Cleared partial transactions and reset transaction type.")

    def select_borrow(self):
        """persist borrow state"""
        app = App.get_running_app()
        app.session.set_transaction_type("borrow")
        self.manager.transition.direction = 'left'
        self.manager.current = 'capture screen'
        print("BORROWING")
    
    def select_return(self):
        """persist return state"""
        app = App.get_running_app()
        app.session.set_transaction_type("return")
        self.manager.transition.direction = 'left'
        self.manager.current = 'capture screen'
        print("RETURNING")