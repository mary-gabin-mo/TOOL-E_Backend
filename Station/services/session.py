"""
PURPOSE:
In-memory session state manager shared across all Station screens.

RUNTIME ROLE:
- Stores user/session identity, transaction mode (borrow/return), and
    in-progress transaction data.
- Provides helper methods for transaction lifecycle transitions.

API ENDPOINTS USED:
- None directly.
"""

import os
from kivy.event import EventDispatcher
from kivy.properties import StringProperty, ObjectProperty, ListProperty, DictProperty, BooleanProperty

class SessionManager(EventDispatcher):
    """
    Holds the state of the current transaction.
    Accessible from any scree via App.get_running_app().session
    """
    
    # Kivy Properties allow the UI to automatically update if these change
    
    # 'borrow' or 'return'
    transaction_type = StringProperty("")
    
    # The User ID (e.g. "30012345")
    user_id = StringProperty(None, allownone=True)
    
    # Full user details from DB (Name, Photo URL, etc.)
    user_data = ObjectProperty(None, allownone=True)
    
    # List of COMPLETED transactions for this session
    # Each item: {'transaction_id': '...', 'img_filename': '...', 'tool_name': '...'}
    transactions = ListProperty([])

    # The current transaction being processed (waiting for tool confirmation)
    current_transaction = DictProperty({})
    
    # Track if the scanned tool was confirmed correct (for return filtering)
    tool_was_confirmed = BooleanProperty(False)

    # Selected return date for the current checkout flow.
    # Stored as a backend-formatted string: YYYY-MM-DD HH:MM:SS
    return_date = StringProperty("")
    
    def reset(self):
        """Clear data for the next user."""
        print("[SESSION] Resetting session state...")
        self.transaction_type = "" # Default to no type selected
        self.user_data = None
        self.user_id = None
        self.transactions = []
        self.current_transaction = {}
        self.tool_was_confirmed = False
        self.return_date = ""
        
    def set_transaction_type(self, type_str):
        if type_str.lower() not in ["borrow", "return"]:
            print(f"[ERROR] Invalid transaction type: {type_str}")
            return
        self.transaction_type = type_str.lower()
        print(f"[SESSION] Transaction Type set to: {self.transaction_type}")
        
    def start_new_transaction(self, transaction_id, img_filename, weight=0):
        """
        Called by Capture Screen immediately after taking a photo.
        Initializes a new pending transaction.
        """
        temp_filename = os.path.basename(img_filename)
        self.current_transaction = {
            "transaction_id": transaction_id,
            "img_filename": temp_filename,  # Final filename for backend persistence; set on confirm
            "temp_img_filename": temp_filename,  # Temp filename uploaded to /identify_tool
            "local_img_path": img_filename, # Keep a backup of the local path for the UI preview
            "tool_name": None,  # Will be filled after ML/User confirmation
            "classification_correct": None, # User feedback on ML prediction
            "weight": int(weight) if weight is not None else 0,
        }
        print(f"[SESSION] Started Transaction: {transaction_id}")

    def set_classification_correct(self, is_correct):
        """
        Updates the 'classification_correct' flag of the current transaction.
        Handles Kivy DictProperty updates correctly.
        """
        if not self.current_transaction:
            print("[SESSION] Warning: No current transaction to update correction status.")
            return

        print(f"[SESSION] Setting classification_correct = {is_correct}")
        # Copy-modify-assign pattern forces Kivy to dispatch the property change event
        tx = dict(self.current_transaction)
        tx['classification_correct'] = is_correct
        self.current_transaction = tx

    def confirm_current_tool(self, tool_name):
        """
        Called by Confirm Screen when user accepts the tool.
        Moves the data from 'current' to the permanent 'transactions' list.
        """
        if not self.current_transaction:
            print("[SESSION] Error: No active transaction to confirm.")
            return

        # Update the tool name
        self.current_transaction["tool_name"] = tool_name

        # Determine final filename for payload. temp_img_filename stays unchanged
        temp_fname = self.current_transaction.get("temp_img_filename") or self.current_transaction.get("img_filename")
        if temp_fname:
            ext = os.path.splitext(os.path.basename(temp_fname))[1] or ".jpg"
            sanitized_tool = tool_name.replace(" ", "")
            action = self.transaction_type.upper() if self.transaction_type else ""
            new_fname = f"{sanitized_tool}_{self.current_transaction['transaction_id']}_{action}{ext}"
            print(f"[SESSION] Final image filename for payload: {new_fname}")
            self.current_transaction["img_filename"] = new_fname

        # Add to the main list
        self.transactions.append(dict(self.current_transaction))
        print(f"[SESSION] Confirmed Tool: {tool_name} (ID: {self.current_transaction['transaction_id']})")
        
        # Clear current
        self.current_transaction = {}

    def update_last_confirmed_tool(self, tool_name):
        """
        Update the most recently confirmed tool entry in-place.
        Used when user goes back from transaction confirmation to edit the last tool.
        """
        if not self.transactions:
            print("[SESSION] Warning: No confirmed transaction exists to update.")
            return

        tx = dict(self.transactions[-1])
        tx["tool_name"] = tool_name

        temp_fname = tx.get("temp_img_filename") or tx.get("img_filename")
        if temp_fname:
            ext = os.path.splitext(os.path.basename(temp_fname))[1] or ".jpg"
            sanitized_tool = tool_name.replace(" ", "")
            action = self.transaction_type.upper() if self.transaction_type else ""
            tx["img_filename"] = f"{sanitized_tool}_{tx['transaction_id']}_{action}{ext}"

        # Reassign list to ensure Kivy property change propagation.
        updated = list(self.transactions)
        updated[-1] = tx
        self.transactions = updated
        print(f"[SESSION] Updated last confirmed tool to: {tool_name}")

    def move_last_confirmed_to_current(self):
        """
        Move the latest confirmed tool back to current_transaction for re-editing.
        """
        if not self.transactions:
            print("[SESSION] Warning: No confirmed transaction exists to move back.")
            return False

        tx_list = list(self.transactions)
        tx = dict(tx_list.pop())
        self.transactions = tx_list
        self.current_transaction = tx
        print(f"[SESSION] Moved confirmed transaction back to current: {tx.get('transaction_id')}")
        return True
        
        