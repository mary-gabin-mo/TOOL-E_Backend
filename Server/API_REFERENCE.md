# TOOL-E Server API Reference

**Base URL:** `http://<server-host>:5000`  
**API Docs:** `http://<server-host>:5000/docs` (Swagger UI)

---

## Health Check

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/` | Server health status |

**Response:**
```json
{"status": "ok", "message": "Server is running"}
```

---

## Authentication & User Validation

### **POST** `/validate_user`
Validates a user by UCID or barcode against the Makerspace Museum DB.

**Request Body:**
```json
{
  "UCID": "1234567",
  "barcode": "A123456789"
}
```

**Response (Success):**
```json
{
  "success": true,
  "user": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "ucid": 1234567
  }
}
```

**Response (Failure):**
```json
{
  "success": false,
  "message": "User not found in database"
}
```

**Notes:**
- Waiver recordDate must be within 365 days
- Searches `MakerspaceCapstone.UCID` for UCID
- Searches `UNICARDBarcode` (with semicolon) for barcode

---

### **POST** `/api/auth/login`
AdminWeb login endpoint (tool_e_db).

**Request Body:**
```json
{
  "email": "admin@example.com",
  "password": "user_id_string"
}
```

**Response (Success):**
```json
{
  "token": "random_token_urlsafe_32",
  "user": {
    "user_id": "admin1",
    "user_name": "Admin Name",
    "email": "admin@example.com"
  }
}
```

**Response (Failure):**
```json
{"detail": "Invalid credentials"}
```
HTTP Status: 401

---

## Tools

### **GET** `/tools`
Returns full tools list with optional stock images.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Drill",
    "size": "Medium",
    "type": "Borrowable",
    "status": "Available",
    "total_quantity": 5,
    "available_quantity": 3,
    "consumed_quantity": 0,
    "trained": true,
    "stock_image_b64": "iVBORw0KGgoAAAANS..."
  }
]
```

---

### **POST** `/tools`
Creates a new tool.

**Request Body:**
```json
{
  "tool_name": "Band Saw",
  "tool_size": "Large",
  "tool_type": "Borrowable",
  "current_status": "Available",
  "total_quantity": 2,
  "available_quantity": 2,
  "consumed_quantity": 0,
  "trained": false
}
```

**Response:**
```json
{"success": true, "message": "Tool created successfully"}
```

---

### **PUT** `/tools/{tool_id}`
Partial update for tool fields.

**Request Body:** (all fields optional)
```json
{
  "tool_name": "Updated Name",
  "tool_size": "Small",
  "tool_type": "Consumable",
  "current_status": "In Use",
  "total_quantity": 10,
  "available_quantity": 8,
  "consumed_quantity": 2,
  "trained": true
}
```

**Response:**
```json
{"success": true, "message": "Tool updated successfully"}
```

**Error:**
```json
{"detail": "Tool not found"}
```
HTTP Status: 404

---

### **PUT** `/tools/{tool_id}/stock-image`
Upload a stock image for a tool.

**Request:** Multipart form-data with image file.

**Response:**
```json
{"success": true, "message": "Stock image updated successfully"}
```

**Errors:**
- HTTP 400: "Only image files are allowed" or "Uploaded file is empty"
- HTTP 404: "Tool not found"

---

## Transactions

### **GET** `/transactions`
Paginated/filterable transaction listing.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | int | - | Filter by user |
| `page` | int | 1 | Page number |
| `limit` | int | 50 | Items per page |
| `start_date` | str | - | Start date (YYYY-MM-DD) |
| `end_date` | str | - | End date (YYYY-MM-DD, inclusive) |
| `sort_by` | str | dateOut | `dateOut` or `dateDue` |
| `sort_order` | str | desc | `asc` or `desc` |
| `search_term` | str | - | Matches user_id, tool_id, or purpose |
| `status` | str | - | Comma-separated: `Borrowed`, `Returned`, `Overdue` |

**Response:**
```json
{
  "items": [
    {
      "transaction_id": "uuid",
      "user_id": 123,
      "user_name": "John Doe",
      "tool_id": 1,
      "tool_name": "Drill",
      "checkout_timestamp": "2026-05-15T10:00:00",
      "desired_return_date": "2026-05-22T00:00:00",
      "return_timestamp": null,
      "quantity": 1,
      "purpose": "Project X",
      "image_path": "Yes/Drill/tx_123.jpg",
      "return_image_path": null,
      "classification_correct": true,
      "weight": 2500.0,
      "status": "Borrowed"
    }
  ],
  "total": 150,
  "page": 1,
  "size": 50,
  "pages": 3
}
```

---

### **GET** `/transactions/unreturned`
Returns only transactions not yet returned.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | int | Optional: filter by user |

**Response:** Same structure as `/transactions`

---

### **POST** `/transactions`
Creates a single transaction.

**Request Body:**
```json
{
  "transaction_id": "uuid",
  "user_id": 123,
  "tool_id": 1,
  "desired_return_date": "2026-05-22",
  "return_timestamp": null,
  "quantity": 1,
  "purpose": "Testing",
  "image_path": "capture_123.jpg",
  "return_image_path": null,
  "classification_correct": true,
  "weight": 2500.0
}
```

**Response:**
```json
{"success": true, "message": "Transaction created successfully"}
```

---

### **POST** `/transactions/batch`
Atomic multi-insert wrapper. Rolls back entire batch if one item fails.

**Request Body:**
```json
{
  "transactions": [
    { "transaction data 1" },
    { "transaction data 2" }
  ]
}
```

**Response:**
```json
{"success": true, "message": "Successfully created 2 transactions"}
```

---

### **PUT** `/transactions/{transaction_id}`
Partial update for transaction fields. Handles return image relocation and JS ISO datetime.

**Request Body:** (all fields optional)
```json
{
  "user_id": 124,
  "tool_id": 2,
  "desired_return_date": "2026-05-29",
  "return_timestamp": "2026-05-15T14:30:00.000Z",
  "quantity": 1,
  "purpose": "Updated purpose",
  "return_image_path": "capture_return.jpg",
  "classification_correct": true,
  "weight": 2500.0
}
```

**Response:**
```json
{"success": true, "message": "Transaction updated successfully"}
```

---

### **DELETE** `/transactions/{transaction_id}`
Deletes a transaction. Restores tool quantity if not yet returned.

**Response:**
```json
{"success": true, "message": "Transaction deleted successfully"}
```

**Error:**
```json
{"detail": "Transaction not found"}
```
HTTP Status: 404

---

### **POST** `/transactions/kiosk`
Kiosk-focused endpoint for bulk submission with image and inventory management.

**Request Body:**
```json
{
  "user_id": "123",
  "transactions": [
    {
      "tool_name": "Drill",
      "img_filename": "capture_drill.jpg",
      "temp_img_filename": "capture_drill.jpg",
      "classification_correct": true
    }
  ]
}
```

**Response:**
```json
{"success": true, "message": "Transaction created successfully"}
```

**Behavior:**
- Auto-creates tools with type "Manual Entry" if unknown
- Decrements `available_quantity` for existing tools
- Moves kiosk image to permanent folder organized by tool name
- If tool's `available_quantity` ≤ 0, increments `total_quantity` instead

---

## Machine Learning

### **POST** `/identify_tool`
Receives an image, runs ML prediction, returns tool class and confidence.

**Request:** Multipart form-data with image file.

**Response:**
```json
{
  "success": true,
  "prediction": "Drill",
  "score": 0.95,
  "all_probabilities": {
    "Drill": 0.95,
    "Saw": 0.03,
    "Other": 0.02
  }
}
```

**Error:**
```json
{"detail": "Prediction failed: ..."}
```
HTTP Status: 500

**Notes:**
- Model: EfficientNet v2-S
- Input size: 384×384
- Device: CUDA if available, else CPU
- Temp image saved with kiosk-provided filename

---

## Analytics

### **GET** `/analytics/dashboard`
Dashboard analytics with live stats and period-based usage.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `period` | str | `1_month` | `1_month` (rolling 30 days) or term ID (e.g., `winter_2026`) |

**Response:**
```json
{
  "live_stats": {
    "total_tools": 25,
    "current_borrowed": 12,
    "current_overdue": 2
  },
  "period_stats": {
    "checkouts": 145,
    "top_tools": [
      {"name": "Drill", "uses": 28},
      {"name": "Saw", "uses": 22}
    ],
    "start_date": "2026-04-15T00:00:00",
    "end_date": "2026-05-15T23:59:59"
  }
}
```

---

## Terms (Academic Periods)

### **GET** `/terms`
Fetches all configured academic terms.

**Response:**
```json
{
  "terms": [
    {
      "id": "winter_2026",
      "name": "Winter 2026",
      "start": "2026-01-01",
      "end": "2026-03-31"
    },
    {
      "id": "spring_2026",
      "name": "Spring 2026",
      "start": "2026-04-01",
      "end": "2026-06-30"
    }
  ]
}
```

---

### **PUT** `/terms`
Replaces full terms list (atomic write to file).

**Request Body:**
```json
{
  "terms": [
    {
      "id": "fall_2026",
      "name": "Fall 2026",
      "start": "2026-09-01",
      "end": "2026-12-31"
    }
  ]
}
```

**Response:** Same as `GET /terms`

**Validation:**
- All fields (`id`, `name`, `start`, `end`) required
- Date format: YYYY-MM-DD
- End date cannot be before start date
- Term IDs must be unique

---

## Error Handling

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Bad request (invalid params/format) |
| 401 | Unauthorized (auth failed) |
| 404 | Not found (resource doesn't exist) |
| 500 | Server error (try again or check logs) |

---

## General Notes

- **CORS:** Open to all origins for LAN/dev usage
- **Authentication:** `/api/auth/login` returns token, but token verification not enforced server-side yet
- **Image Storage:** Temp images in `captured_images/temp`, organized to `captured_images/{Yes,No}/{ToolName}/`
- **Timestamps:** MySQL format; JS ISO timestamps auto-normalized
- **API Documentation:** Swagger UI available at `/docs` endpoint
