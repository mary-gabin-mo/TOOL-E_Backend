"""
PURPOSE:
Lets user choose which unreturned transaction item to close during return flow.

RUNTIME ROLE:
- Fetches unreturned tools for current user.
- Submits return updates and optional return-image metadata.

API ENDPOINTS USED:
- GET /transactions/unreturned (via `APIClient.get_user_unreturned_tools`)
- PUT /transactions/{transaction_id} (via `APIClient.return_tools`)
"""

from kivy.app import App
from View.baseScreen import BaseScreen
import threading
from kivy.clock import mainthread
from kivy.properties import DictProperty, BooleanProperty, StringProperty, ListProperty
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from datetime import datetime

class ReturnToolItem(RecycleDataViewBehavior, ButtonBehavior, BoxLayout):
    """Custom list item for RecycleView with row-tap selection."""
    tool_data = DictProperty()
    is_active = BooleanProperty(False)
    text = StringProperty()
    secondary_text = StringProperty()
    bg_color = ListProperty([1, 1, 1, 1])
    
    def refresh_view_attrs(self, rv, index, data):
        """ Catch and handle the view changes """
        self._rv_index = index
        return super().refresh_view_attrs(rv, index, data)

    def on_release(self):
        """Triggered by ButtonBehavior when the row is tapped."""
        self.toggle_active()

    def toggle_active(self):
        """Toggle checkbox state on row tap."""
        new_state = not self.is_active
        self.set_active_state(new_state)

    def set_active_state(self, is_active):
        self.is_active = is_active
        app = App.get_running_app()
        if hasattr(app, 'manager_screens'):
            screen = app.manager_screens.get_screen('tool return selection screen')
            if screen:
                screen.on_checkbox_change(self.tool_data, is_active, getattr(self, '_rv_index', None))

class ToolReturnSelectionScreen(BaseScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected_tx_id = None
        self._selected_tool_data = None
    
    def on_enter(self):
        """
        Populate the list with non-returned tools.
        Filter by tool type if the scanned tool was confirmed correct.
        """
        app = App.get_running_app()
        
        # Get the predicted tool name from the current transaction
        predicted_tool = None
        tool_was_confirmed = getattr(app.session, 'tool_was_confirmed', False)
        
        if hasattr(app.session, 'identified_tool_data') and app.session.identified_tool_data:
            predicted_tool = app.session.identified_tool_data.get('prediction', None)

        # If recognition failed or was rejected, we show all tools.
        # Trigger alert state (red LED + beep) only for that path.
        if hasattr(app, 'hardware') and hasattr(app.hardware, 'set_led_state'):
            if tool_was_confirmed and predicted_tool:
                app.hardware.set_led_state('transaction')
            else:
                app.hardware.set_led_state('alert')
        
        # Clear existing selection
        self._selected_tx_id = None
        self._selected_tool_data = None
        
        # Show loading state
        self.ids.title_label.text = "Loading tools..."
        self.ids.empty_message.opacity = 1
        self.ids.empty_message.text = "Please wait..."
        self.ids.continue_btn.disabled = True
        self.ids.tool_recycle_view.data = []
        
        # Fetch non-returned tools for this user from API in background
        threading.Thread(
            target=self._fetch_non_returned_tools_thread, 
            args=(tool_was_confirmed, predicted_tool)
        ).start()

    def on_leave(self):
        """Reset LED to normal transaction state when leaving this screen."""
        app = App.get_running_app()
        if hasattr(app, 'hardware') and hasattr(app.hardware, 'set_led_state'):
            app.hardware.set_led_state('transaction')

    def _fetch_non_returned_tools_thread(self, tool_was_confirmed, predicted_tool):
        app = App.get_running_app()
        user_id = None
        if hasattr(app.session, 'user_data') and app.session.user_data:
            user_id = app.session.user_data.get('ucid') or app.session.user_data.get('id')
            
        non_returned_tools = []
        if user_id:
            try:
                response = app.api_client.get_user_unreturned_tools(user_id)
                if response.get('success'):
                    non_returned_tools = response.get('data', [])
            except Exception as e:
                print(f"[ERROR] Exception fetching unreturned tools: {e}")
                
        self._update_tools_ui(non_returned_tools, tool_was_confirmed, predicted_tool)

    @mainthread
    def _update_tools_ui(self, non_returned_tools, tool_was_confirmed, predicted_tool):
        print(f"[DEBUG] Fetched {len(non_returned_tools)} tools")
        
        # Filter tools if the scanned tool was confirmed correct
        if tool_was_confirmed and predicted_tool:
            # Show only tools matching the predicted type
            filtered_tools = [tool for tool in non_returned_tools if isinstance(tool, dict) and tool.get('tool_name') == predicted_tool]
            self.ids.title_label.text = f"Select {predicted_tool} to Return"
        else:
            # Show all non-returned tools
            filtered_tools = [tool for tool in non_returned_tools if isinstance(tool, dict)]
            self.ids.title_label.text = "Select Tool to Return"
        
        # Display filtered tools
        if not filtered_tools:
            self.ids.empty_message.opacity = 1
            self.ids.empty_message.text = "No unreturned tools found"
            self.ids.continue_btn.disabled = True
            self.ids.tool_recycle_view.data = []
        else:
            self.ids.empty_message.opacity = 0
            
            rv_data = []
            for tool in filtered_tools:
                borrow_date = self._format_date_only(tool.get('borrow_date') or tool.get('checkout_timestamp'))
                due_date = self._format_date_only(tool.get('due_date') or tool.get('desired_return_date'))
                tool_name = tool.get('tool_name') or 'Unknown Tool'
                
                rv_data.append({
                    "text": tool_name,
                    "secondary_text": f"Borrowed: {borrow_date}   |   Due: {due_date}",
                    "tool_data": tool,
                    "is_active": False,
                    "bg_color": [1, 1, 1, 1]
                })
            
            self.ids.tool_recycle_view.data = rv_data

    def _format_date_only(self, value):
        """Normalize common API datetime/date formats to YYYY-MM-DD for list display."""
        if not value:
            return 'N/A'

        text = str(value).strip()
        if not text:
            return 'N/A'

        # Fast path for ISO-like values: keep only the date segment.
        if len(text) >= 10 and text[4] == '-' and text[7] == '-':
            return text[:10]

        # Fallback for non-ISO strings that still parse with datetime.
        for fmt in ('%Y/%m/%d %H:%M:%S', '%Y/%m/%d', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y'):
            try:
                return datetime.strptime(text, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue

        return text
    
    def _fetch_non_returned_tools(self):
        """
        Fetch non-returned tools for the current user from the API.
        Returns a list of dictionaries with tool information.
        """
        app = App.get_running_app()
        
        # Get user ID from session
        user_id = None
        if hasattr(app.session, 'user_data') and app.session.user_data:
            user_id = app.session.user_data.get('ucid') or app.session.user_data.get('id')
        
        if not user_id:
            print("[ERROR] No user ID found in session")
            return []
        
        # Call API to get non-returned tools
        try:
            response = app.api_client.get_user_unreturned_tools(user_id)
            if response.get('success'):
                return response.get('data', [])
            else:
                print(f"[ERROR] Failed to fetch unreturned tools: {response.get('error')}")
                return []
        except Exception as e:
            print(f"[ERROR] Exception fetching unreturned tools: {e}")
            # Return mock data for testing
            return [
                {
                    'tool_id': 1,
                    'tool_name': 'Hammer',
                    'borrow_date': '2026-02-15',
                    'due_date': '2026-03-15'
                },
                {
                    'tool_id': 2,
                    'tool_name': 'Hammer',
                    'borrow_date': '2026-02-20',
                    'due_date': '2026-03-20'
                },
                {
                    'tool_id': 3,
                    'tool_name': 'Screwdriver',
                    'borrow_date': '2026-02-25',
                    'due_date': '2026-03-25'
                }
            ]
    
    def on_checkbox_change(self, tool_data, is_active, rv_index=None):
        """Single-select behavior: only one transaction can be active at a time."""
        if not tool_data:
            return
            
        tx_id = tool_data.get('transaction_id')
        if not tx_id:
            return

        rv = self.ids.tool_recycle_view

        if is_active:
            # Select only one item: deactivate all rows first.
            for i, item in enumerate(rv.data):
                row_active = item.get('tool_data', {}).get('transaction_id') == tx_id
                rv.data[i]['is_active'] = row_active
                rv.data[i]['bg_color'] = [0.86, 0.93, 1, 1] if row_active else [1, 1, 1, 1]
            self._selected_tx_id = tx_id
            self._selected_tool_data = tool_data
        else:
            # Allow unselecting the currently selected row.
            if self._selected_tx_id == tx_id:
                self._selected_tx_id = None
                self._selected_tool_data = None
            for i, item in enumerate(rv.data):
                if item.get('tool_data', {}).get('transaction_id') == tx_id:
                    rv.data[i]['is_active'] = False
                    rv.data[i]['bg_color'] = [1, 1, 1, 1]
                    break
            
        rv.refresh_from_data()
        self.ids.continue_btn.disabled = self._selected_tx_id is None
    
    def confirm_selection(self):
        """
        Collect selected tool, store it in session, then navigate to confirmation.
        """
        app = App.get_running_app()
        
        if not self._selected_tool_data or not self._selected_tx_id:
            print("[UI] No tool selected.")
            return

        selected_tools = []

        # Return capture metadata comes from the current scanned image in this session.
        current_tx = getattr(app.session, 'current_transaction', {}) if hasattr(app, 'session') else {}
        temp_img_filename = current_tx.get('temp_img_filename')
        classification_correct = current_tx.get('classification_correct')
        captured_img_name = current_tx.get('img_filename') or temp_img_filename
        img_ext = '.jpg'
        if captured_img_name:
            img_ext = (captured_img_name.rsplit('.', 1)[-1] and f".{captured_img_name.rsplit('.', 1)[-1]}") if '.' in captured_img_name else '.jpg'
        
        tx_id = self._selected_tx_id
        d = self._selected_tool_data
        tool_name = d.get('tool_name', "Unknown Tool")
        tx_payload = {
            'transaction_id': tx_id,
            'tool_id': d.get('tool_id', None),
            'tool_name': tool_name
        }

        # Attach captured image metadata to the selected return transaction.
        if temp_img_filename:
            safe_tool = tool_name.replace(' ', '')
            tx_payload['temp_img_filename'] = temp_img_filename
            tx_payload['return_img_filename'] = f"{safe_tool}_{tx_id}_RETURN{img_ext}"
            tx_payload['classification_correct'] = classification_correct

        selected_tools.append(tx_payload)

        print("[UI] Selected 1 tool for return")
        
        # Disable button during processing
        self.ids.continue_btn.disabled = True
        
        threading.Thread(target=self._return_tools_thread, args=(selected_tools,)).start()
        
    def _return_tools_thread(self, selected_tools):
        app = App.get_running_app()
        try:
            result = app.api_client.return_tools(selected_tools)
        except Exception as e:
            result = {'success': False, 'error': str(e)}
            
        self._handle_return_result(result, selected_tools)
        
    @mainthread
    def _handle_return_result(self, result, selected_tools):
        app = App.get_running_app()
        # self.ids.continue_btn.text = "Confirm Return"
        
        if result.get('success') or result.get('count', 0) > 0:
            # Store processed transactions in session so confirmation screen can show them
            app.session.transactions = selected_tools
            
            # Navigate to return confirmation screen
            self.go_to('return confirmation screen')
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"[ERROR] Failed to return tools: {error_msg}")

            # Keep user on this screen and allow retry.
            self.ids.continue_btn.disabled = False
            self.ids.empty_message.opacity = 1
            self.ids.empty_message.text = f"Return failed. Please try again.\n{error_msg}"
    
    def go_back(self):
        """Return to tool confirmation screen."""
        self.go_to('tool confirm screen')
