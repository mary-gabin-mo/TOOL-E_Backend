"""
PURPOSE:
Displays return success state and offers options to end session or return more tools.

RUNTIME ROLE:
- Final confirmation UI for return workflow.
- Controls session reset/continuation navigation.

API ENDPOINTS USED:
- None directly.
"""

from View.baseScreen import BaseScreen

class ReturnConfirmationScreen(BaseScreen):
    
    def on_enter(self):
        """Called when the screen is displayed."""
        from kivy.app import App
        app = App.get_running_app()
        
        # Display confirmation message with the returned tool name
        transactions = getattr(app.session, 'transactions', [])
        
        if transactions:
            tool_name = transactions[0].get('tool_name', 'Unknown Tool')
            self.ids.message_display.text = f"Successfully returned {tool_name}!"
        else:
            self.ids.message_display.text = "Return confirmed!"
    
    def return_to_menu(self):
        """Clear session data and return to welcome screen."""
        from kivy.app import App
        app = App.get_running_app()
        app.session.reset()
        
        # Navigate to welcome screen (homepage)
        self.go_to('welcome screen')

    def return_more_tools(self):
        """Start another return flow by scanning more tools."""
        from kivy.app import App
        app = App.get_running_app()

        # Keep the user logged in, clear only transaction-scoped state.
        app.session.transactions = []
        app.session.current_transaction = {}
        app.session.tool_was_confirmed = False
        app.session.set_transaction_type("return")

        # Go directly back to scan/capture for another return.
        self.go_to('capture screen')
    
    def continue_with_user(self):
        """Navigate to action selection screen while keeping user logged in."""
        from kivy.app import App
        app = App.get_running_app()
        
        # Clear only transaction-specific data, keep user_data
        app.session.transactions = []
        app.session.current_transaction = {}
        app.session.transaction_type = "borrow"  # Reset to default
        
        # Navigate to action selection screen
        self.go_to('action selection screen')
