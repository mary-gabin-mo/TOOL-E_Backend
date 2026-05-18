# TOOL-E Server

Backend API for TOOL-E, built with FastAPI.

This service handles:
- user validation against Makerspace records
- admin login for AdminWeb
- tool inventory CRUD
- kiosk and admin transaction workflows
- ML image-based tool identification
- dashboard analytics
- file-backed academic term management for analytics periods

## Overview

- Framework: FastAPI
- DB access: SQLAlchemy + PyMySQL
- ML stack: PyTorch + torchvision + Pillow
- API docs: Swagger at /docs
- Default local API port: 5000

Core app entrypoint:
- app.main:app

Server startup script:
- server_entrypoint.py

## Project Structure

- app/main.py: app creation, middleware, startup hooks, router registration
- app/database.py: environment-based DB engine creation
- app/models.py: Pydantic request/response models
- app/routers/: API route handlers
- app/services/: ML, image handling, term storage utilities
- sql/: schema and seed scripts for tool_e_db
- captured_images/: temp and permanent image storage

## Prerequisites

- Python 3.10+
- MySQL server
- Accessible Makerspace DB named Museum (for /validate_user)
- Local Tool-E DB named tool_e_db

## Installation

1. From the Server folder, install dependencies:

```bash
pip install -r requirements.txt
```

2. Create Server/.env.local with required variables.

## Environment Variables

Required for database connections:

- MAKERSPACE_DB_USERNAME
- MAKERSPACE_DB_PASSWORD
- MAKERSPACE_DB_HOST
- MAKERSPACE_DB_PORT
- TOOL_E_DB_USERNAME
- TOOL_E_DB_PASSWORD

Optional:

- IMAGE_STORAGE_PATH
  - Overrides the default image storage root.
  - If unset, images are stored in Server/captured_images.

Notes:
- app/database.py loads .env.local.
- Tool-E DB host/port are currently hardcoded as localhost:3306.

## Database Setup (tool_e_db)

Run these scripts in order:

1. sql/create_users_table.sql
2. sql/create_tools_table.sql
3. sql/create_transactions_table.sql
4. sql/insert_tools_data.sql (optional sample tool rows)

Schema summary:
- users: admin/staff identities used by /api/auth/login
- tools: inventory metadata and quantities
- transactions: borrow/return records plus image metadata and ML correctness flag

## Running the Server

Start in development mode:

```bash
python server_entrypoint.py
```

Behavior:
- host: 0.0.0.0
- port: 5000
- reload: enabled

Health check:

- GET /
  - returns status payload when server is running

Swagger UI:

- http://localhost:5000/docs

## Startup Behavior

On startup, app/main.py does the following:

1. Loads ML model from app/services/efficientnet_finetuned_v2.pth
2. Ensures image temp directory exists
3. Cleans old temp images (older than 24 hours)

Also includes request logging middleware that prints incoming method/path and response status.

## API Reference

### Authentication and User Validation

POST /validate_user
- Validates a user by UCID or barcode against the Museum DB.
- UCID path: searches MakerspaceCapstone.UCID
- Barcode path: appends semicolon before lookup in UNICARDBarcode
- Fails if waiver recordDate is older than 365 days
- Response shape: success flag + optional user object

POST /api/auth/login
- AdminWeb login endpoint
- Looks up user by email in tool_e_db.users
- Current password rule: password must equal the user_id string
- Returns random token + user profile on success

### Tools

GET /tools
- Returns full tools list
- Includes optional stock_image_b64 field when image data exists

POST /tools
- Inserts a new tool row

PUT /tools/{tool_id}
- Partial update for tool fields
- Returns 404 if tool does not exist

### Transactions

GET /transactions
- Paginated/filterable transaction listing
- Query params:
  - user_id
  - page (default 1)
  - limit (default 50)
  - start_date
  - end_date (inclusive day logic)
  - sort_by: dateOut or dateDue
  - sort_order: asc or desc
  - search_term (matches user_id, tool_id, purpose)
  - status (comma-separated: Borrowed, Returned, Overdue)

GET /transactions/unreturned
- Returns only rows where return_timestamp is NULL
- Optional user_id filter

POST /transactions
- Creates a single transaction
- If image_path is provided, attempts to move image from temp to permanent folder

POST /transactions/batch
- Atomic multi-insert wrapper around the single-transaction logic
- Rolls back entire batch if one item fails

PUT /transactions/{transaction_id}
- Partial update endpoint
- Handles JS ISO return timestamps and normalizes for MySQL
- Return image updates attempt temp->permanent move before persisting filename

DELETE /transactions/{transaction_id}
- Deletes transaction row by id

POST /transactions/kiosk
- Kiosk-focused bulk-ish endpoint using custom payload
- Parses user_id, resolves tool by tool_name
- If tool is unknown and not Other, auto-creates tool with type Manual Entry
- Decrements available quantity for existing tools
- Moves kiosk image into permanent folder and records transaction

### Machine Learning

POST /identify_tool
- Accepts multipart file upload
- Saves incoming image to temp storage (filename is kiosk-controlled)
- Runs prediction via loaded EfficientNet model
- Returns prediction, score, and all class probabilities

### Analytics

GET /analytics/dashboard
- Query param: period
- Supported period values:
  - 1_month (rolling 30 days)
  - any term id from /terms (for example winter_2026)
- Response sections:
  - live_stats: total tools, currently borrowed, currently overdue
  - period_stats: checkouts, top_tools, start_date, end_date

### Terms (File-Backed, No DB)

GET /terms
- Reads terms from app/services/terms.json

PUT /terms
- Replaces full terms list
- Validation:
  - id/name/start/end required
  - dates must be YYYY-MM-DD
  - end date cannot be before start date
  - term ids must be unique

Terms storage details:
- File: app/services/terms.json
- Writes are atomic (temp file + replace)
- In-process lock prevents concurrent write races

## Image Storage Behavior

Image service behavior is implemented in app/services/image_service.py.

Path conventions:
- temp uploads: captured_images/temp
- permanent: captured_images/Yes/{ToolName} or captured_images/No/{ToolName}

Filename behavior:
- Can preserve provided filename or rename using transaction id
- API stores final filename in DB fields image_path / return_image_path

## ML Model Behavior

ML service is implemented in app/services/ml_service.py.

Details:
- Model architecture: efficientnet_v2_s
- Weights file: app/services/efficientnet_finetuned_v2.pth
- Class names file: app/services/class_names.json
- Input size: 384x384
- Device: CUDA if available, otherwise CPU

If model file is missing, ML features remain disabled until model is provided.

## Utility Scripts

- debug_routes.py
  - Prints registered FastAPI routes for quick debugging.

- reset_database.py
  - Destructive helper.
  - Truncates transactions and resets tool quantities/status.

- sql/temp_gen_seeds.py
  - Generates SQL seed inserts for transactions.

## Current Implementation Notes

- CORS is open to all origins for LAN/dev usage.
- No auth middleware currently protects route groups.
- /api/auth/login returns a token but token verification is not enforced server-side yet.
- A small Server/package.json exists but Python runtime is the primary backend path.
