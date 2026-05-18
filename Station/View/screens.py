"""
PURPOSE:
Central screen registry for the Station app.

RUNTIME ROLE:
- Imports all screen classes and maps runtime route names to view classes.
- Consumed by `main.py` during app/screen manager initialization.

API ENDPOINTS USED:
- None directly.
"""

from View.WelcomeScreen.welcome_screen import WelcomeScreen
from View.ActionSelectionScreen.action_selection_screen import ActionSelectionScreen
from View.CaptureScreen.capture_screen import CaptureScreen
from View.ManualEntryScreen.manual_entry_screen import ManualEntryScreen
from View.ToolConfirmScreen.tool_confirm_screen import ToolConfirmScreen
from View.ToolSelectionScreen.tool_selection_screen import ToolSelectionScreen
from View.ToolReturnSelectionScreen.tool_return_selection_screen import ToolReturnSelectionScreen
from View.TransactionConfirmScreen.transaction_confirm_screen import TransactionConfirmScreen
from View.UserErrorScreen.user_error_screen import UserErrorScreen
from View.CheckoutConfirmationScreen.checkout_confirmation_screen import CheckoutConfirmationScreen
from View.ReturnConfirmationScreen.return_confirmation_screen import ReturnConfirmationScreen
from View.ManualToolEntryScreen.manual_tool_entry_screen import ManualToolEntryScreen

screens = {
    "welcome screen": {
        "view": WelcomeScreen
    },
    "manual entry screen": {
        "view": ManualEntryScreen
    },
    "action selection screen": {
        "view": ActionSelectionScreen
    },
    "capture screen": {
        "view": CaptureScreen
    },
    "tool confirm screen": {
        "view": ToolConfirmScreen
    },
    "tool select screen": {
        "view": ToolSelectionScreen
    },
    "tool return selection screen": {
        "view": ToolReturnSelectionScreen
    },
    "transaction confirm screen": {
        "view": TransactionConfirmScreen
    },
    "checkout confirmation screen": {
        "view": CheckoutConfirmationScreen
    },
    "return confirmation screen": {
        "view": ReturnConfirmationScreen
    },
    "user error screen": {
        "view": UserErrorScreen
    },
    "manual tool entry screen": {
        "view": ManualToolEntryScreen
    },
}