"""
PURPOSE:
Manual fallback for entering tool name when prediction/selection paths fail.

RUNTIME ROLE:
- Writes manual tool name into session transaction state.
- Routes user back into confirmation/selection flow.

API ENDPOINTS USED:
- None directly.
"""

from kivy.app import App
from kivy.properties import ObjectProperty
from View.baseScreen import BaseScreen

class ManualToolEntryScreen(BaseScreen):
    
    def on_enter(self):
        """Called every time the screen is displayed."""
        self.ids.manual_tool_input.text = ""
        self.ids.confirm_button.disabled = True
        self.ids.manual_tool_input.bind(text=self.on_text_change)

        app = App.get_running_app()
        if hasattr(app, 'hardware') and hasattr(app.hardware, 'set_led_state'):
            app.hardware.set_led_state('alert')
        
        # Optionally, set focus to input field automatically
        # Clock.schedule_once(lambda dt: setattr(self.ids.manual_tool_input, 'focus', True), 0.5)
        
    def on_leave(self):
        self.ids.manual_tool_input.unbind(text=self.on_text_change)
        
    def on_text_change(self, instance, value):
        """Enable confirm button only if text is provided."""
        if value.strip():
            self.ids.confirm_button.disabled = False
        else:
            self.ids.confirm_button.disabled = True

    def confirm_tool_name(self):
        """User clicked Confirm or pressed Enter."""
        tool_name = self.ids.manual_tool_input.text.strip()
        if not tool_name:
            return
            
        app = App.get_running_app()
        if hasattr(app, 'session'):
            session = app.session
            
            # Similar to ToolSelectionScreen, check if there's a current transaction
            if not session.current_transaction:
                print("[UI] Dev Mode: Creating dummy transaction for manual selection.")
                from datetime import datetime
                
                now = datetime.now()
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                milliseconds = int(now.microsecond / 1000)
                timestamp_id = f"{timestamp}-{milliseconds:03d}"
                filename = f"{timestamp_id}.jpg" 
                
                session.start_new_transaction(timestamp_id, filename)
                
            if session.current_transaction.get('classification_correct') is None:
                 session.set_classification_correct(False)
                 
            session.confirm_current_tool(tool_name)

        if hasattr(app, 'hardware') and hasattr(app.hardware, 'set_led_state'):
            app.hardware.set_led_state('transaction')
            
        self.go_to('transaction confirm screen')

    def go_back(self):
        """Go back to tool selection screen."""
        self.go_to('tool select screen')
