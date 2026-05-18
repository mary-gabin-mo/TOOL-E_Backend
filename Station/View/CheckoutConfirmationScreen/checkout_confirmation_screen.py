"""
PURPOSE:
Displays successful checkout summary and offers navigation to next workflow step.

RUNTIME ROLE:
- Final confirmation UI for borrow flow after backend submission succeeds.

API ENDPOINTS USED:
- None directly.
"""

from View.baseScreen import BaseScreen
from kivy.factory import Factory
from datetime import datetime

class CheckoutConfirmationScreen(BaseScreen):
    
    def on_enter(self):
        # Get the date from the session or previous screen
        from kivy.app import App
        app = App.get_running_app()
        
        # Get the return date from session if available
        return_date = getattr(app.session, 'return_date', None)
        
        if return_date:
            if isinstance(return_date, datetime):
                date_str = return_date.strftime('%b %d, %Y')
            elif isinstance(return_date, str):
                try:
                    parsed = datetime.strptime(return_date, "%Y-%m-%d %H:%M:%S")
                    date_str = parsed.strftime('%b %d, %Y')
                except ValueError:
                    date_str = return_date
            else:
                date_str = str(return_date)

            self.ids.date_display.text = f"{date_str}"
        else:
            self.ids.date_display.text = "Checkout confirmed!"
            
        # Add summary of items
        transactions = getattr(app.session, 'transactions', [])
        
        list_container = self.ids.summary_list_container
        list_container.clear_widgets()
        
        if not transactions:
            list_container.add_widget(
                Factory.ReadonlyToolListItem(text="No tools tracked")
            )
        else:
            for idx, tx in enumerate(transactions, 1):
                tool_name = tx.get('tool_name', 'Unknown Tool')
                lbl = Factory.ReadonlyToolListItem(text=f"{idx}. {tool_name}")
                list_container.add_widget(lbl)
    
    def return_to_menu(self):
        # Clear session data
        from kivy.app import App
        app = App.get_running_app()
        app.session.reset()
        
        # Navigate to welcome screen (homepage)
        self.go_to('welcome screen')
    
    def continue_with_user(self):
        """Navigate to action selection screen while keeping user logged in."""
        from kivy.app import App
        app = App.get_running_app()
        
        # Clear only transaction-specific data, keep user_data
        app.session.scanned_tools = []
        app.session.return_date = ""
        app.session.transaction_type = "borrow"  # Reset to default
        
        # Navigate to action selection screen
        self.go_to('action selection screen')
