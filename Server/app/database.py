"""
PURPOSE:
Creates and exports SQLAlchemy engine connections for the user database
(Museum/Makerspace) and local TOOL-E database.

API ENDPOINTS USED:
- None directly. Router modules import `engine_users` and `engine_tools`.
"""

import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv('.env.local')

# --- Database 1: User Database (Museum/Makerspace) ---
MAKERSPACE_DB_USERNAME = os.getenv('MAKERSPACE_DB_USERNAME')
MAKERSPACE_DB_PASSWORD = os.getenv('MAKERSPACE_DB_PASSWORD')
MAKERSPACE_DB_HOST = os.getenv('MAKERSPACE_DB_HOST')
MAKERSPACE_DB_PORT = os.getenv('MAKERSPACE_DB_PORT')

USER_DB_URL = f"mysql+pymysql://{MAKERSPACE_DB_USERNAME}:{MAKERSPACE_DB_PASSWORD}@{MAKERSPACE_DB_HOST}:{MAKERSPACE_DB_PORT}/{'Museum'}"

# --- Database 2: Tools Database (Local Tool-E DB) ---
TOOL_E_DB_USERNAME = os.getenv('TOOL_E_DB_USERNAME')
TOOL_E_DB_PASSWORD = os.getenv('TOOL_E_DB_PASSWORD')
TOOLS_DB_URL = f"mysql+pymysql://{TOOL_E_DB_USERNAME}:{TOOL_E_DB_PASSWORD}@localhost:3306/tool_e_db"

# --- Global Database Engines ---
# Create engines once to maintain connection pools
engine_users = create_engine(USER_DB_URL, pool_pre_ping=True, pool_recycle=3600)
engine_tools = create_engine(TOOLS_DB_URL, pool_pre_ping=True, pool_recycle=3600)
