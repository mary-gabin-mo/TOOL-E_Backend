"""
PURPOSE:
HTTP client layer for all Station-to-Server communication.

RUNTIME ROLE:
- Wraps backend calls with retries/timeouts and response normalization.
- Provides a single API surface for UI screens and workflow logic.

API ENDPOINTS USED:
- POST /validate_user
- POST /identify_tool
- POST /transactions/kiosk
- PUT /transactions/{transaction_id}
- GET /transactions/unreturned
- GET /tools
"""

import requests
import os
import json
from datetime import datetime
import time
from kivy.event import EventDispatcher
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Import settings from the config file
from config import (
    API_VALIDATE_USER,
    API_IDENTIFY_TOOL,
    API_TRANSACTION,
    API_GET_TOOLS,
    NETWORK_TIMEOUT
)

class APIClient(EventDispatcher):
    """
    Handles all HTTP requests to the FastAPI Backend.
    OPTIMIZATION: Uses connection pooling and retry strategy for better performance.
    """
    
    def __init__(self):
        super().__init__()
        # OPTIMIZATION: Create a session with connection pooling
        # This reuses TCP connections and reduces overhead
        self.session = requests.Session()
        
        # OPTIMIZATION: Add retry strategy for transient network failures
        retry_strategy = Retry(
            total=2,  # Retry max 2 times for failed requests
            backoff_factor=0.5,  # Wait 0.5s, 1s between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=2, pool_maxsize=2)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Cache tool payload (including stock image blobs) to avoid repeated downloads.
        self._tools_cache_data = None
        self._tools_cache_at = 0.0
        self._tools_cache_ttl_sec = 300
    
    def validate_user(self, id):
        """
        Checks if a user exists and has a valid waiver.
        
        Args:
            id (str): The barcode from the card or UCID typed manually
            
        Returns:
            dict: {'success': True, 'data': user_dict} OR {'success': False, 'error': str}
        """
        
        # Determine if id is UCID or barcode
        if id.isdigit(): # if id contains digits only, it is UCID
            ucid = id;
            print(f"[API] Validating User: {ucid=}...")
            payload = {"barcode": None, "UCID": ucid} # Distinguish whether it's barcode or UCID in the server with regex
        
        else: # barcode is alphanumeric
            barcode = id;
            print(f"[API] Validating User: {barcode=}...")
            payload = {"barcode": barcode, "UCID": None} # Distinguish whether it's barcode or UCID in the server with regex
            
        response = None
        try:
            # OPTIMIZATION: Use pooled session instead of raw requests
            response = self.session.post(
                API_VALIDATE_USER,
                json=payload,
                timeout=NETWORK_TIMEOUT
            )
            response.raise_for_status() # Raise error for 4xx/5xx codes
            
            # Success!
            res = response.json()
            print(f"{res=}")
            if res.get('success'): 
                print(f"[API] Success: {res}")
                return res
            else:
                print(f"[API] Waiver Expired Error: {res.get('message')}")
                return {'success': False, 'error': res.get('message')}
        
        except requests.exceptions.ConnectionError:
            print("[API] Connection Error: Is the server running?")
            return {'success': False, 'error': "Could not connect to server."}
        
        except requests.exceptions.Timeout:
            print("[API] Timeout Error")
            return {'success': False, 'error': "Server reuqest timed out."}
            
        except requests.exceptions.RequestException as e:
            # Handle 404 (User not found) - when user not found in the db
            if response is not None and response.status_code == 404:
                return {'success': False, 'error': "User not found in database."}
            
            print(f"[API] Error: {e}")
            return {'success': False, 'error': f"System Error: {e}"}
        
    def get_tools(self, force_refresh=False):
        """
        Get all tools from the database.
        
        Returns:
            list: List of tool dictionaries
        """
        now = time.time()
        if not force_refresh and self._tools_cache_data is not None:
            if now - self._tools_cache_at < self._tools_cache_ttl_sec:
                return self._tools_cache_data

        print("[API] Fetching all tools...")
        try:
            # OPTIMIZATION: Use pooled session
            response = self.session.get(
                API_GET_TOOLS,
                timeout=NETWORK_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            self._tools_cache_data = data
            self._tools_cache_at = now
            return data
            
        except Exception as e:
            print(f"[API] Error fetching tools: {e}")
            if self._tools_cache_data is not None:
                return self._tools_cache_data
            return []

    def invalidate_tools_cache(self):
        self._tools_cache_data = None
        self._tools_cache_at = 0.0

    def upload_tool_image(self, image_path):
        """
        Uploads the captured image for recognition.
        
        Args:
            image_path(str): Full path to the .jpg file on the Pi.
        
        Returns:
            dict: {'sucess': True, 'tool': 'Hammer', 'conf': 0.98} OR Error dict
        """ 
        print(f"[API] Uploading image: {image_path}...")
        
        if not os.path.exists(image_path):
            return{'success': False, 'error': "Image file not found on disk."}
        
        try:
            # Open file in binary mode
            filename = os.path.basename(image_path)
            with open(image_path, 'rb') as img_file:
                upload_name = os.path.basename(image_path)
                # 'file' matches the parameter name in the FastAPI endpoint
                # Value is a tuple: (filename, file_object, content_type)
                files = {'file': (filename, img_file, 'image/jpeg')}
                
                # OPTIMIZATION: Use pooled session
                response = self.session.post(
                    API_IDENTIFY_TOOL,
                    files=files,
                    timeout=10.0 # Give images some more time than simple JSON
                )
                
            response.raise_for_status()
            data = response.json()
            
            print(f"[API] Recognition Result: {data}")
            return {'success': True, 'data': data}
        
        except Exception as e:
            print(f"[API] Upload Failed: {e}")
            return {'success': False, 'error': "Recognition failed. Please try again."}
        
        
    def submit_transaction(self, transaction_data):
        """
        Finalizes the Checkout or Return.
        
        Args:
            transaction_data (dict): {
                "user_id": "...",
                "tool_id": "...",
                "action": "borrow"|"return",
                ...
            }
        """
        print(f"[API] Submitting Transaction: {transaction_data}")
        
        try: 
            # OPTIMIZATION: Use pooled session
            response = self.session.post(
                f"{API_TRANSACTION}/kiosk",
                json=transaction_data,
                timeout=NETWORK_TIMEOUT
            )
            response.raise_for_status()
            
            print("[API] Transaction Recorded Successfully.")
            return {'success': True}
        
        except Exception as e:
            print(f"[API] Transaction Failed: {e}")
            return {'success': False, 'error': "Could not record transaction."}
    
    def return_tools(self, transactions):
        """
        Mark tools as returned. 
        Args:
           transactions (list): List of dicts, each with 'transaction_id'.
        """
        print(f"[API] Returning {len(transactions)} tools...")
        success_count = 0
        errors = []
        
        current_time = datetime.now().isoformat()
        
        for tx in transactions:
            tx_id = tx.get('transaction_id')
            if not tx_id:
                errors.append(f"Missing transaction_id for tool: {tx}")
                continue

            tool_name = tx.get('tool_name', 'UnknownTool')
            sanitized_tool = str(tool_name).replace(' ', '')
            ext = '.jpg'
            original_name = tx.get('img_filename') or tx.get('image_path')
            if original_name:
                _, guessed_ext = os.path.splitext(os.path.basename(str(original_name)))
                if guessed_ext:
                    ext = guessed_ext

            return_image_name = f"{sanitized_tool}_{tx_id}_RETURN{ext}"
                
            payload = {
                "return_timestamp": current_time,
            }

            if tx.get('return_img_filename'):
                payload["return_image_path"] = tx.get('return_img_filename')
            if tx.get('temp_img_filename'):
                payload["temp_img_filename"] = tx.get('temp_img_filename')
            if tx.get('classification_correct') is not None:
                payload["classification_correct"] = tx.get('classification_correct')

            print(f"[API] Return payload for {tx_id}: {payload}")
            
            try:
                # Update the transaction
                # API_TRANSACTION endpoint is base_url/transactions
                # OPTIMIZATION: Use pooled session
                response = self.session.put(
                    f"{API_TRANSACTION}/{tx_id}",
                    json=payload,
                    timeout=NETWORK_TIMEOUT
                )
                response.raise_for_status()
                print(f"[API] Successfully returned transaction {tx_id}")
                success_count += 1
            except Exception as e:
                print(f"[API] Failed to return transaction {tx_id}: {e}")
                errors.append(f"Failed to return transaction {tx_id}: {e}")
                
        if success_count > 0:
            return {'success': True, 'count': success_count, 'errors': errors}
        else:
            return {'success': False, 'error': f"No tools returned. Errors: {errors}"}

    def get_user_unreturned_tools(self, user_id):
        """
        Fetch all unreturned tools for a specific user.
        
        Args:
            user_id (str): The user's UCID
            
        Returns:
            dict: {'success': True, 'data': [tool_list]} OR {'success': False, 'error': str}
        """
        print(f"[API] Fetching unreturned tools for user: {user_id}")
        
        try:
            # Use the query param route which is confirmed to work
            candidate_calls = [
                (f"{API_TRANSACTION}/unreturned", {"user_id": user_id}),
            ]

            last_error = None
            payload = None

            for url, params in candidate_calls:
                try:
                    response = requests.get(url, params=params, timeout=NETWORK_TIMEOUT)
                    response.raise_for_status()
                    payload = response.json()
                    break
                except Exception as e:
                    last_error = e

            if payload is None:
                raise last_error or Exception("No response from unreturned-tools endpoint")

            # Normalize backend response into a list for UI code.
            if isinstance(payload, list):
                tools = payload
            elif isinstance(payload, dict):
                tools = (
                    payload.get("data")
                    or payload.get("items")
                    or payload.get("tools")
                    or payload.get("unreturned_tools")
                    or []
                )
            else:
                tools = []

            if not isinstance(tools, list):
                tools = []

            print(f"[API] Found {len(tools)} unreturned tools")
            return {'success': True, 'data': tools}

        except Exception as e:
            print(f"[API] Error fetching unreturned tools: {e}")
            return {'success': False, 'error': str(e)}