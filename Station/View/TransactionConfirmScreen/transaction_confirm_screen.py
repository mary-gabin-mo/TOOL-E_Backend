"""
PURPOSE:
Final step for borrow workflow where user selects return date/purpose and submits.

RUNTIME ROLE:
- Builds kiosk transaction payload from session data.
- Submits checkout and handles success/failure UI transitions.

API ENDPOINTS USED:
- POST /transactions/kiosk (via `APIClient.submit_transaction`)
"""

import os
import threading
from kivy.clock import mainthread
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout as KivyBoxLayout
from kivy.uix.label import Label as KivyLabel
from kivy.uix.textinput import TextInput
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ListProperty
from kivy.factory import Factory
from View.baseScreen import BaseScreen
from widgets.calendar_popup import CalendarPopup
from datetime import datetime, date


class BorderedBox(ButtonBehavior, KivyBoxLayout):
    """BoxLayout with clickable behavior and a dynamic colored border."""
    line_color = ListProperty([1, 0, 0, 1])
    bg_color = ListProperty([0.95, 0.95, 0.95, 1])


class CourseCodeInput(TextInput):
    """TextInput restricted to 4 uppercase letters followed by 3 digits (e.g. CSCI101)."""
    def insert_text(self, substring, from_undo=False):
        current = self.text
        filtered = ''
        for ch in substring:
            pos = len(current) + len(filtered)
            if pos >= 7:
                break
            if pos < 4:
                if ch.isalpha():
                    filtered += ch.upper()
            else:
                if ch.isdigit():
                    filtered += ch
        super().insert_text(filtered, from_undo=from_undo)

class TransactionConfirmScreen(BaseScreen):
    
    return_date = None
    purpose = None # 'Academic Course' or 'Personal Project'
    
    def on_enter(self):
        """Reset state when entering screen."""
        self.return_date = None
        self.purpose = None
        self.ids.course_code_box.opacity = 0
        self.ids.course_code_box.disabled = True
        self.ids.course_code_box.pos_hint = {'x': 10, 'y': 0}
        self.ids.course_code_input.disabled = True
        self.ids.course_code_input.text = ''
        self.ids.team_name_box.opacity = 0
        self.ids.team_name_box.disabled = True
        self.ids.team_name_box.pos_hint = {'x': 10, 'y': 0}
        self.ids.team_name_input.disabled = True
        self.ids.team_name_input.text = ''
        
        app = App.get_running_app()
        if hasattr(app, 'hardware') and hasattr(app.hardware, 'set_led_state'):
            app.hardware.set_led_state('transaction')
        transaction_type = getattr(app.session, 'transaction_type', 'borrow')
                
        # For returns, we don't need a return date - skip directly to finish
        if transaction_type == "return":
            print("[UI] Guard: return flow cannot use TransactionConfirmScreen. Redirecting.")
            self.go_to('tool return selection screen')
            return
        
        # For borrows, show date selector
        self.ids.date_box.opacity = 1
        self.ids.date_box.size_hint_y = None
        self.ids.confirm_finish_btn.disabled = True
        self.ids.confirm_finish_btn.text = "CONFIRM CHECKOUT"
        
        # Reset the red border box visuals
        self.ids.date_box.line_color = (1, 0, 0, 1)  # Red border
        self.ids.date_label.text = "Tap to select Return Date"
        self.ids.date_label.color = (0.5, 0.5, 0.5, 1)
        
        # Load tool info from session
        transactions = getattr(app.session, 'transactions', [])
        
        # Clear existing items in the list
        list_container = self.ids.tool_list_container
        list_container.clear_widgets()
        
        if not transactions:
            # Fallback if list is empty (shouldn't happen in flow)
            list_container.add_widget(
                Factory.ReadonlyToolListItem(
                    text="No tools scanned",
                )
            )
        else:
            # Populate list with all scanned tools
            for tx in transactions:
                # Handle dictionary or simple string
                tool_name = tx.get('tool_name', 'Unknown Tool')
                list_container.add_widget(
                    Factory.ReadonlyToolListItem(
                        text=tool_name,
                    )
                )
        
    def open_calendar(self):
        """Open the custom popup"""
        popup = CalendarPopup(callback=self.on_date_selected)
        popup.open()
        
    def on_date_selected(self, date_obj):
        """Called by the popup when user hits Confirm."""
        self.return_date = date_obj
        
        # Update UI to show success
        self.ids.date_label.text = f"Returning on: {date_obj.strftime('%b %d, %Y')}"
        self.ids.date_label.color = (0, 0, 0, 1)  # Black text
        
        # Change border from Red to Blue/Grey to indicate "Done"
        self.ids.date_box.line_color = (0.2, 0.6, 0.8, 1)
        
        self.check_can_finish()
        
    def select_purpose(self, selected_purpose):
        self.purpose = selected_purpose

        all_btns = [
            (self.ids.btn_academic, "Academic Course"),
            (self.ids.btn_personal, "Personal Project"),
            (self.ids.btn_team, "Team"),
            (self.ids.btn_research, "Research"),
        ]
        for btn, label in all_btns:
            if label == selected_purpose:
                btn.base_color = (0.2, 0.6, 0.8, 1)  # Blue
                btn.color = (1, 1, 1, 1)
            else:
                btn.base_color = (0.9, 0.9, 0.9, 1)  # Grey
                btn.color = (0, 0, 0, 1)

        # Show/hide course code input
        if selected_purpose == "Academic Course":
            self.ids.course_code_box.pos_hint = {'x': 0, 'y': 0}
            self.ids.course_code_box.opacity = 1
            self.ids.course_code_box.disabled = False
            self.ids.course_code_input.disabled = False
        else:
            self.ids.course_code_box.pos_hint = {'x': 10, 'y': 0}
            self.ids.course_code_box.opacity = 0
            self.ids.course_code_box.disabled = True
            self.ids.course_code_input.disabled = True
            self.ids.course_code_input.text = ''

        # Show/hide team name input
        if selected_purpose == "Team":
            self.ids.team_name_box.pos_hint = {'x': 0, 'y': 0}
            self.ids.team_name_box.opacity = 1
            self.ids.team_name_box.disabled = False
            self.ids.team_name_input.disabled = False
        else:
            self.ids.team_name_box.pos_hint = {'x': 10, 'y': 0}
            self.ids.team_name_box.opacity = 0
            self.ids.team_name_box.disabled = True
            self.ids.team_name_input.disabled = True
            self.ids.team_name_input.text = ''

        self.check_can_finish()

    def on_course_code_changed(self, text):
        self.check_can_finish()

    def on_team_name_changed(self, text):
        self.check_can_finish()

    def check_can_finish(self):
        date_ok = self.return_date is not None
        purpose_ok = self.purpose is not None
        if self.purpose == "Academic Course":
            code = self.ids.course_code_input.text
            extra_ok = len(code) == 7 and code[:4].isalpha() and code[4:].isdigit()
        elif self.purpose == "Team":
            extra_ok = len(self.ids.team_name_input.text.strip()) > 0
        else:
            extra_ok = True
        self.ids.confirm_finish_btn.disabled = not (date_ok and purpose_ok and extra_ok)

    def finish_transaction(self):
        app = App.get_running_app()

        if app.session.transaction_type == "return":
            print("[UI] Guard: return flow cannot submit via TransactionConfirmScreen. Redirecting.")
            self.go_to('tool return selection screen')
            return
        
        print(f"Checkout Transaction Confirmed! Return Date: {self.return_date}")
        # Format Date for Backend (YYYY-MM-DD HH:MM:SS)
        if isinstance(self.return_date, date) and not isinstance(self.return_date, datetime):
            formatted_date = f"{self.return_date.strftime('%Y-%m-%d')} 23:59:59"
        else:
            formatted_date = self.return_date.strftime("%Y-%m-%d %H:%M:%S")

        # Safe User ID retrieval
        user_id = getattr(app.session, 'user_id', '')
        user_dict = app.session.user_data or {}

        if not user_id and user_dict:
             # Fallback: try to get ID from the user dictionary if user_id property is empty
             # API returns 'ucid', checking both just in case
             user_id = user_dict.get('ucid') or user_dict.get('id', '')

        # Get User Name (First + Last)
        first_name = user_dict.get('first_name', '')
        last_name = user_dict.get('last_name', '')
        user_name = f"{first_name} {last_name}".strip()

        # Construct the final payload for the API
        # strip directory from any image paths so only the filename is sent
        raw_tx = getattr(app.session, 'transactions', [])
        tx_list = []
        for tx in raw_tx:
            tx_copy = dict(tx)
            img = tx_copy.get('img_filename')
            if img:
                tx_copy['img_filename'] = os.path.basename(img)
            temp_img = tx_copy.get('temp_img_filename')
            if temp_img:
                tx_copy['temp_img_filename'] = os.path.basename(temp_img)
            tx_list.append(tx_copy)

        if self.purpose == "Academic Course":
            purpose_str = f"Academic Course: {self.ids.course_code_input.text}"
        elif self.purpose == "Team":
            purpose_str = f"Team: {self.ids.team_name_input.text.strip()}"
        else:
            purpose_str = self.purpose

        final_payload = {
            "user_id": str(user_id),
            "user_name": user_name or "Unknown User",
            "return_date": formatted_date,
            "purpose": purpose_str,
            "transactions": tx_list
        }

        # Persist selected date so checkout confirmation can display it.
        app.session.return_date = formatted_date
        
        print(f"[UI] Submitting Transaction via APIClient...")
        
        # Disable button during processing
        self.ids.confirm_finish_btn.disabled = True
        self.ids.confirm_finish_btn.text = "Submitting..."

        # Call API logic using the centralized API Client in a thread
        threading.Thread(target=self._submit_transaction_thread, args=(final_payload,)).start()
        
    def _submit_transaction_thread(self, final_payload):
        app = App.get_running_app()
        try:
            response = app.api_client.submit_transaction(final_payload)
        except Exception as e:
            response = {'success': False, 'error': str(e)}
        self._handle_submission_result(response)

    def _cleanup_local_images(self):
        """Delete local captured images only after successful submission."""
        app = App.get_running_app()
        for tx in getattr(app.session, 'transactions', []):
            img_path = tx.get('local_img_path')
            if not img_path:
                continue
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
                    print(f"[UI] Deleted image file after confirmation: {img_path}")
            except Exception as e:
                print(f"[UI] Warning: could not delete image {img_path}: {e}")
        
    @mainthread
    def _handle_submission_result(self, response):
        app = App.get_running_app()
        self.ids.confirm_finish_btn.disabled = False
        self.ids.confirm_finish_btn.text = "CONFIRM CHECKOUT"

        if response.get('success'):
            print("Transaction Success")
            self._cleanup_local_images()
            self.go_to('checkout confirmation screen')
        else:
            print(f"Transaction Failed: {response.get('error')}")
            # You might want to add a UI popup here to alert the user
