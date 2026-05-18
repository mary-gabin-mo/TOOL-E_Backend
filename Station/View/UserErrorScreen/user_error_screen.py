"""
PURPOSE:
Displays user-facing error messages and provides a safe return path to welcome.

RUNTIME ROLE:
- Generic error surface for validation/network/flow failures.

API ENDPOINTS USED:
- None directly.
"""

from kivy.app import App
from View.baseScreen import BaseScreen

class UserErrorScreen(BaseScreen):
    
    def set_error_message(self, message):
        """
        Updates the error label with dynamic text.
        Call this method BEFORE switching to this screen.
        """
        self.ids.error_label.text = str(message)
    def go_to_main(self):
        """Resets the session and goes back to the Welcome screen."""
        app = App.get_running_app()
        if hasattr(app, 'session'):
            app.session.reset()
            
        self.go_back('welcome screen') 