"""
PURPOSE:
Manual tool list selection UI used when auto-classification is uncertain or rejected.

RUNTIME ROLE:
- Loads tool list, allows user selection, and updates current transaction metadata.
- Supports optional expansion/preview behavior for tool entries.

API ENDPOINTS USED:
- GET /tools (via `APIClient.get_tools`)
"""

from kivy.app import App
from kivy.properties import ObjectProperty, DictProperty, StringProperty, ListProperty
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
import threading
import base64
import hashlib
import os
from kivy.clock import mainthread

from View.baseScreen import BaseScreen

class SelectableToolItem(RecycleDataViewBehavior, ButtonBehavior, BoxLayout):
    text = StringProperty('')
    secondary_text = StringProperty('')
    tool_data = DictProperty()
    bg_color = ListProperty([1, 1, 1, 1])
    preview_source = StringProperty('')
    preview_height = ObjectProperty(0)
    row_height = ObjectProperty(92)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

    def handle_selection(self):
        app = App.get_running_app()
        # Find the active screen using app.manager_screens
        if hasattr(app, 'manager_screens'):
            screen = app.manager_screens.get_screen('tool select screen')
            if screen:
                screen.on_tool_selected(self, self.tool_data)

class ToolSelectionScreen(BaseScreen):
    
    selected_tool = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._expanded_tool_id = None
        self._preview_cache = {}
    
    def on_enter (self):
        """Called every time the screen is displayed."""
        app = App.get_running_app()
        if hasattr(app, 'session') and app.session.transaction_type == "return":
            print("[UI] Guard: return flow cannot use ToolSelectionScreen. Redirecting.")
            self.go_to('tool return selection screen')
            return

        if hasattr(app, 'hardware') and hasattr(app.hardware, 'set_led_state'):
            # Manual selection mode should always signal alert state.
            app.hardware.set_led_state('alert')

        self.selected_tool = None
        self._expanded_tool_id = None
        self.ids.next_button.disabled = True
        self.populate_list()
        
    def populate_list(self):
        """Clears the list and fetches tool items using API data in a thread."""
        tool_rv = self.ids.tool_recycle_view
        
        # Show a loading placeholder
        tool_rv.data = [{
            "text": "Loading tools...",
            "secondary_text": "",
            "tool_data": {},
            "bg_color": [1, 1, 1, 1],
            "preview_source": "",
            "preview_height": 0,
            "row_height": 92,
        }]
        
        threading.Thread(target=self._fetch_tools_thread).start()
        
    def _fetch_tools_thread(self):
        app = App.get_running_app()
        all_tools = app.api_client.get_tools()
        self._update_ui_with_tools(all_tools)
        
    @mainthread
    def _update_ui_with_tools(self, all_tools):
        # 1. Clear previous items so we don't duplicate
        tool_rv = self.ids.tool_recycle_view
        
        if not all_tools:
            tool_rv.data = [{
                "text": "No API tools found",
                "secondary_text": "",
                "tool_data": {},
                "bg_color": [1, 1, 1, 1],
                "preview_source": "",
                "preview_height": 0,
                "row_height": 92,
            }]
        
        else:
            rv_data = []
            # 3. Create items
            for tool_obj in all_tools:
                preview_source = self._materialize_preview_image(tool_obj)
                rv_data.append({
                    "text": f"{tool_obj['name']}",
                    "secondary_text": "",
                    "tool_data": tool_obj,
                    "bg_color": [1, 1, 1, 1],
                    "preview_source": preview_source,
                    "preview_height": 0,
                    "row_height": 92,
                })

            # 4. Add "Other" Option to the bottom
            other_tool = {"id": 0, "name": "Other", "status": "Manual", "available_quantity": "-"}
            rv_data.append({
                "text": "Other / Not Listed",
                "secondary_text": "",
                "tool_data": other_tool,
                "bg_color": [1, 1, 1, 1],
                "preview_source": "",
                "preview_height": 0,
                "row_height": 92,
            })
            
            tool_rv.data = rv_data
            
    def on_tool_selected(self, item_widget, tool_data):
        """
        Receives the full tool dictionary
        """
        if not tool_data:
            return
            
        print(f"[UI] User manually selected: {tool_data.get('name')} (ID: {tool_data.get('id')})")
        
        self.selected_tool = tool_data
        self.ids.next_button.disabled = False

        selected_id = tool_data.get('id')
        if self._expanded_tool_id == selected_id:
            self._expanded_tool_id = None
        else:
            self._expanded_tool_id = selected_id
        
        # Visual feedback: highlight selected row in data model
        rv = self.ids.tool_recycle_view
        for i, item in enumerate(rv.data):
            item_id = item.get('tool_data', {}).get('id')
            has_preview = bool(item.get('preview_source'))
            if item_id == selected_id:
                rv.data[i]['bg_color'] = [0.86, 0.93, 1, 1]
                if self._expanded_tool_id == item_id and has_preview:
                    rv.data[i]['preview_height'] = 220
                    rv.data[i]['row_height'] = 312
                else:
                    rv.data[i]['preview_height'] = 0
                    rv.data[i]['row_height'] = 92
            else:
                rv.data[i]['bg_color'] = [1, 1, 1, 1]
                rv.data[i]['preview_height'] = 0
                rv.data[i]['row_height'] = 92
        
        rv.refresh_from_data()

    def _materialize_preview_image(self, tool_obj):
        """Decode base64 image blobs from API and write temp preview files for Kivy Image."""
        if not isinstance(tool_obj, dict):
            return ""

        raw_b64 = tool_obj.get('stock_image_b64')
        if not raw_b64:
            return ""

        mime = "image/jpeg"
        encoded = raw_b64
        if isinstance(raw_b64, str) and raw_b64.startswith("data:"):
            try:
                header, encoded = raw_b64.split(",", 1)
                if ";base64" in header:
                    mime = header.split(":", 1)[1].split(";", 1)[0] or mime
            except ValueError:
                return ""

        if not isinstance(encoded, str):
            return ""

        cache_key = f"{tool_obj.get('id')}:{hashlib.md5(encoded.encode('utf-8')).hexdigest()}"
        cached_path = self._preview_cache.get(cache_key)
        if cached_path and os.path.exists(cached_path):
            return cached_path

        ext = ".jpg"
        if "png" in mime:
            ext = ".png"
        elif "webp" in mime:
            ext = ".webp"

        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except Exception:
            return ""

        app = App.get_running_app()
        base_cache_dir = getattr(app, 'user_data_dir', '') if app else ''
        if not base_cache_dir:
            base_cache_dir = os.path.join(os.getcwd(), '.cache')
        cache_dir = os.path.join(base_cache_dir, 'tool_e_stock_previews')
        os.makedirs(cache_dir, exist_ok=True)
        filename = f"tool_{tool_obj.get('id', 'x')}_{cache_key.split(':', 1)[1]}{ext}"
        file_path = os.path.join(cache_dir, filename)

        try:
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as f:
                    f.write(image_bytes)
            self._preview_cache[cache_key] = file_path
            return file_path
        except Exception:
            return ""
        
    def proceed(self):
        """
        User clicked Next. Confirm this tool and save to transaction list.
        Compatible with both 'Camera Flow' and 'Dev Flow'.
        """
        if self.selected_tool and self.selected_tool['name'] == "Other":
            self.go_to('manual tool entry screen')
            return

        app = App.get_running_app()
        if hasattr(app, 'session') and app.session.transaction_type == "return":
            print("[UI] Guard: return flow cannot proceed via ToolSelectionScreen. Redirecting.")
            self.go_to('tool return selection screen')
            return

        app = App.get_running_app()
        if hasattr(app, 'session'):
            session = app.session

            # Ensure there is an active transaction for this correction flow.
            if not session.current_transaction:
                print("[UI] Dev Mode: Creating dummy transaction for manual selection.")

                from datetime import datetime

                now = datetime.now()
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                milliseconds = int(now.microsecond / 1000)
                timestamp_id = f"{timestamp}-{milliseconds:03d}"
                filename = f"{timestamp_id}.jpg"

                session.start_new_transaction(timestamp_id, filename)

            # Manual correction should keep classification as incorrect.
            session.set_classification_correct(False)

            # Replace predicted tool shown on ToolConfirm screen with user's selected tool.
            selected_name = self.selected_tool.get('name', 'Unknown Tool')
            session.identified_tool_data = {
                'prediction': selected_name,
                'score': None,
                'source': 'manual',
            }

        # Return to ToolConfirm so scan-more/finish decisions happen in one place.
        self.go_to('tool confirm screen')
