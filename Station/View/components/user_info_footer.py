"""
PURPOSE:
Reusable footer component showing current user and transaction context.

RUNTIME ROLE:
- Binds to session state and updates footer labels across screens.
- Keeps user context visible during kiosk flow.

API ENDPOINTS USED:
- None directly.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.app import App

class UserInfoFooter(BoxLayout):
    """
    Footer component that displays current user info and transaction type.
    Automatically updates when session data changes.
    """    
    user_name = StringProperty("Guest")
    user_ucid = NumericProperty(0)
    user_email = StringProperty("--")
    transaction_type = StringProperty("-----")
    transaction_color = ListProperty([0.5, 0.5, 0.5, 1])  # Transaction label text color
    is_user_logged_in = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind_session()
    
    def bind_session(self):
        """Bind to SessionManager to auto-update when user data changes"""
        app = App.get_running_app()
        if hasattr(app, 'session'):
            session = app.session
            session.bind(user_data=self.on_user_data_change)
            session.bind(transaction_type=self.on_transaction_type_change)
            
            # Set default color
            self.transaction_color = [0.5, 0.5, 0.5, 1]  # Grey
            
            # Set initial values if session already has data
            if session.user_data:
                self.on_user_data_change(session, session.user_data)
            else:
                self.update_no_user_state()
            # Always sync transaction type
            self.on_transaction_type_change(session, session.transaction_type)
    
    def on_user_data_change(self, session, user_data):
        """Called when session.user_data is updated"""
        if user_data:
            self.user_name = user_data.get('first_name', 'Unknown')
            # Convert UCID to int, default to 0 if not available or invalid
            ucid_value = user_data.get('ucid', '0')
            try:
                self.user_ucid = int(ucid_value) if ucid_value else 0
            except (ValueError, TypeError):
                self.user_ucid = 0
            self.user_email = user_data.get('email', '--')
            self.is_user_logged_in = True
            # Update transaction type display when user logs in
            transaction_type = session.transaction_type
            if transaction_type.lower() == 'return':
                self.transaction_type = 'RETURN'
                self.transaction_color = [0.2, 0.6, 0.2, 1]  # Green for return
            elif transaction_type.lower() == 'borrow':
                self.transaction_type = 'BORROW'
                self.transaction_color = [0.76, 0.19, 0.20, 1]  # Red for borrow
            else:
                self.transaction_type = "-----"
                self.transaction_color = [0.5, 0.5, 0.5, 1]  # Grey for no type
        else:
            self.update_no_user_state()
            self.is_user_logged_in = False
    
    def update_no_user_state(self):
        """Reset UI when user logs out"""
        self.user_name = "Guest"
        self.user_ucid = 0
        self.user_email = "--"
        self.transaction_type = "-----"
        self.transaction_color = [0.5, 0.5, 0.5, 1]  # Grey
    
    def on_transaction_type_change(self, session, transaction_type):
        """Called when session.transaction_type is updated"""
        # Only update display if user is logged in
        if self.is_user_logged_in:
            if transaction_type.lower() == 'return':
                self.transaction_type = 'RETURN'
                self.transaction_color = [0.2, 0.6, 0.2, 1]  # Green for return
            elif transaction_type.lower() == 'borrow':
                self.transaction_type = 'BORROW'
                self.transaction_color = [0.76, 0.19, 0.20, 1]  # Red for borrow
            else:
                self.transaction_type = "-----"
                self.transaction_color = [0.5, 0.5, 0.5, 1]  # Grey for no type
