"""
PURPOSE:
Presents captured tool image/prediction and asks user to confirm or reject.

RUNTIME ROLE:
- Branches workflow to borrow or return paths based on session mode.
- Persists classification feedback and image lifecycle decisions.

API ENDPOINTS USED:
- None directly.
"""

import os
from kivy.app import App
from kivy.properties import StringProperty
from View.baseScreen import BaseScreen

class ToolConfirmScreen(BaseScreen):
    predicted_name = None
    # Mode controls layout variations. 'confirm' (default) or 'return'
    mode = StringProperty('confirm')

    def on_enter(self):
        """
        Populate the UI with data from the Session when the screen opens.
        """
        app = App.get_running_app()
        if hasattr(app, 'hardware') and hasattr(app.hardware, 'set_led_state'):
            app.hardware.set_led_state('transaction')
        
        # 1. Get the image path from current transaction, or fall back to the
        # latest confirmed one when user returned from transaction confirm.
        img_path = ""
        if hasattr(app, 'session') and app.session.current_transaction:
            # Display the local full path on the screen (not the server's uuid name)
            img_path = app.session.current_transaction.get('local_img_path', app.session.current_transaction.get('img_filename', ''))
        elif hasattr(app, 'session') and getattr(app.session, 'transactions', None):
            last_tx = app.session.transactions[-1]
            img_path = last_tx.get('local_img_path', last_tx.get('img_filename', ''))
        
        self.ids.tool_image.source = img_path
        self.ids.tool_image.reload() # Force reload if file changed

        # 2. Get the Prediction from the API result
        # We assume CaptureScreen saved the API result to 'session.identified_tool_data'
        tool_name = "Unknown Tool"
        score = ""
        
        if hasattr(app, 'session') and hasattr(app.session, 'identified_tool_data'):
            data = app.session.identified_tool_data
            if data:
                tool_name = data.get('prediction', 'Unknown')
                score_source = data.get('source')
                confidence = data.get('score', None)
                if score_source == 'manual':
                    score = "Manually selected"
                elif isinstance(confidence, (int, float)):
                    score = f"{int(confidence * 100)}% Match"
                else:
                    score = ""
        
        self.predicted_name = tool_name
        self.ids.tool_name_label.text = tool_name
        self.ids.confidence_label.text = score
        # Set layout mode based on transaction type (affects which buttons are shown)
        try:
            tx_type = app.session.transaction_type if hasattr(app, 'session') else None
        except Exception:
            tx_type = None
        self.mode = 'return' if tx_type == 'return' else 'confirm'

    def _delete_current_image(self, tx_override=None):
        """Delete the temporary captured image for the current or provided transaction."""
        app = App.get_running_app()
        if not hasattr(app, 'session'):
            return

        tx = tx_override if tx_override is not None else app.session.current_transaction
        if not tx and getattr(app.session, 'transactions', None):
            tx = app.session.transactions[-1]
        if not tx:
            return
        # Prefer local absolute path from capture step; keep fallbacks for compatibility.
        img_path = tx.get('local_img_path') or tx.get('img_filename')

        # If only a filename is present, resolve it against current working directory.
        if img_path and not os.path.isabs(img_path):
            candidate = os.path.abspath(img_path)
            if os.path.exists(candidate):
                img_path = candidate

        if img_path and os.path.isabs(img_path) and os.path.exists(img_path):
            try:
                os.remove(img_path)
                print(f"[UI] Deleted image file {img_path} after tool confirmation.")
            except Exception as e:
                print(f"[UI] Warning: could not delete image {img_path}: {e}")

    def _remove_last_confirmed_transaction(self):
        """Remove and return the latest confirmed transaction from session."""
        app = App.get_running_app()
        if not hasattr(app, 'session'):
            return None

        tx_list = list(getattr(app.session, 'transactions', []))
        if not tx_list:
            return None

        removed = dict(tx_list.pop())
        app.session.transactions = tx_list
        print(f"[SESSION] Removed last confirmed transaction: {removed.get('transaction_id')}")
        return removed

    def confirm_scan_more(self):
        """
        User clicked YES. Confirm this tool and save to transaction list.
        """
        app = App.get_running_app()
        
        if hasattr(app, 'session'):
            # Preserve explicit manual-correction flag if user previously rejected prediction.
            existing_flag = app.session.current_transaction.get('classification_correct') if app.session.current_transaction else None
            if existing_flag is None:
                app.session.set_classification_correct(True)
        
        # Check if this is a return transaction
        if app.session.transaction_type == "return":
            # Mark tool as confirmed
            app.session.tool_was_confirmed = True
            # Keep the captured image for the return selection flow
            self.go_to('tool return selection screen')
        else:
            # For borrows, confirm and scan more
            if hasattr(app, 'session'):
                if app.session.current_transaction:
                    self._delete_current_image()
                    app.session.confirm_current_tool(self.predicted_name)
                else:
                    app.session.update_last_confirmed_tool(self.predicted_name)
            self.go_to('capture screen') 
        
    def confirm_finish(self):
        """
        User clicked YES. Confirm this tool and save to transaction list.
        """
        app = App.get_running_app()
        
        if hasattr(app, 'session'):
            # Preserve explicit manual-correction flag if user previously rejected prediction.
            existing_flag = app.session.current_transaction.get('classification_correct') if app.session.current_transaction else None
            if existing_flag is None:
                app.session.set_classification_correct(True)
        
        # Check if this is a return transaction
        if app.session.transaction_type == "return":
            # Mark tool as confirmed
            app.session.tool_was_confirmed = True
            # Keep the captured image so return selection can attach it
            self.go_to('tool return selection screen')
        else:
            # For borrows, confirm and finish.
            # Do NOT delete image here; keep it until final transaction confirmation.
            if hasattr(app, 'session'):
                if app.session.current_transaction:
                    app.session.confirm_current_tool(self.predicted_name)
                else:
                    app.session.update_last_confirmed_tool(self.predicted_name)
            self.go_to('transaction confirm screen') 

    def reject_tool(self):
        """
        User clicked NO. Go to the manual selection list or tool return selection.
        """
        app = App.get_running_app()
        
        if hasattr(app, 'session'):
            app.session.set_classification_correct(False)
        
        # Check if this is a return transaction
        if app.session.transaction_type == "return":
            # Mark tool as NOT confirmed (will show all unreturned tools)
            app.session.tool_was_confirmed = False
            # Keep the captured image for return selection/attachment
            self.go_to('tool return selection screen')
        else:
            # For borrows, go to manual selection
            if hasattr(app, 'session') and not app.session.current_transaction:
                app.session.move_last_confirmed_to_current()
            self.go_to('tool select screen')

    def go_back_to_capture(self):
        """Back button handler for confirm screen."""
        app = App.get_running_app()

        removed_tx = None
        if hasattr(app, 'session'):
            # If there is no active pending tx, user is editing an already confirmed item.
            # Remove that latest confirmed item before returning to capture.
            if not app.session.current_transaction:
                removed_tx = self._remove_last_confirmed_transaction()

        # Delete the image associated with the removed or current transaction.
        self._delete_current_image(tx_override=removed_tx)
        self.go_back('capture screen')
