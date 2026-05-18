"""
PURPOSE:
Shared base class for Station screens with common navigation helpers.

RUNTIME ROLE:
- Standardizes forward/back navigation behavior and transaction cancel flow.
- Parent class inherited by most screen implementations.

API ENDPOINTS USED:
- None directly.
"""

from kivy.app import App
from kivy.uix.screenmanager import Screen
from View.components.user_info_footer import UserInfoFooter

class BaseScreen(Screen):
    """
    Parent class for all screens.
    Includes helper methods for navigation.
    All screens should include the UserInfoFooter at the bottom.
    """
    
    def go_to(self, screen_name):
        """Forward navigation (Slide Left)"""
        # 'self.manager' is automatically available in all Screens
        if self.manager:
            self.manager.transition.direction = 'left'
            self.manager.current = screen_name 
            
    def go_back(self, screen_name):
        """Backward navigation (Slide Right)"""   
        if self.manager:
            self.manager.transition.direction = 'right'
            self.manager.current = screen_name
            
    def cancel_transaction(self):
        """
        User clicked CANCEL. Reset session and go back to welcome screen.
        """
        app = App.get_running_app()
        if hasattr(app, 'session'):
            app.session.reset()
        self.go_back('welcome screen')
