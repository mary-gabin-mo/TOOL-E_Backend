"""
PURPOSE:
Provides tool catalog CRUD operations and stock image upload/update.

API ENDPOINTS OWNED:
- GET /tools
- POST /tools
- PUT /tools/{tool_id}
- PUT /tools/{tool_id}/stock-image

"""

import base64

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import text
from app.models import ToolInput, ToolUpdate
from app.database import engine_tools

router = APIRouter()

@router.get("/tools")
async def get_tools():
    """Get all tools from the database"""
    with engine_tools.connect() as conn:
        result = conn.execute(text("""
            SELECT
                tool_id,
                tool_name,
                tool_size,
                tool_type,
                current_status,
                total_quantity,
                available_quantity,
                consumed_quantity,
                trained,
                image
            FROM tools
        """))
        tools = []
        for row in result:
             image_value = row.image
             image_b64 = None

             if image_value is not None:
                 if isinstance(image_value, memoryview):
                     image_value = image_value.tobytes()
                 if isinstance(image_value, bytes):
                     image_b64 = base64.b64encode(image_value).decode("ascii")
                 elif isinstance(image_value, str):
                     image_b64 = image_value

             tools.append({
                 "id": row.tool_id,
                 "name": row.tool_name,
                 "size": row.tool_size,
                 "type": row.tool_type,
                 "status": row.current_status,
                 "total_quantity": row.total_quantity,
                 "available_quantity": row.available_quantity,
                 "consumed_quantity": row.consumed_quantity,
                 "trained": True if (row.trained == 1 or str(row.trained) == '1') else False,
                 "stock_image_b64": image_b64,
             })
        return tools

@router.post("/tools")
async def create_tool(tool: ToolInput):
    with engine_tools.connect() as conn:
        query = text("""
            INSERT INTO tools (tool_name, tool_size, tool_type, current_status, total_quantity, available_quantity, consumed_quantity, trained)
            VALUES (:name, :size, :type, :status, :total, :available, :consumed, :trained)
        """)
        conn.execute(query, {
            "name": tool.tool_name,
            "size": tool.tool_size,
            "type": tool.tool_type,
            "status": tool.current_status,
            "total": tool.total_quantity,
            "available": tool.available_quantity,
            "consumed": tool.consumed_quantity,
            "trained": tool.trained
        })
        conn.commit()
    return {"success": True, "message": "Tool created successfully"}

@router.put("/tools/{tool_id}")
async def update_tool(tool_id: int, tool: ToolUpdate):
    with engine_tools.connect() as conn:
        check = conn.execute(text("SELECT tool_id FROM tools WHERE tool_id = :id"), {"id": tool_id}).fetchone()
        if not check:
            raise HTTPException(status_code=404, detail="Tool not found")

        updates = []
        params = {"id": tool_id}
        
        if tool.tool_name is not None:
            updates.append("tool_name = :name")
            params["name"] = tool.tool_name
        if tool.tool_size is not None:
            updates.append("tool_size = :size")
            params["size"] = tool.tool_size
        if tool.tool_type is not None:
             updates.append("tool_type = :type")
             params["type"] = tool.tool_type
        if tool.current_status is not None:
             updates.append("current_status = :status")
             params["status"] = tool.current_status
        if tool.total_quantity is not None:
             updates.append("total_quantity = :total")
             params["total"] = tool.total_quantity
        if tool.available_quantity is not None:
             updates.append("available_quantity = :available")
             params["available"] = tool.available_quantity
        if tool.consumed_quantity is not None:
             updates.append("consumed_quantity = :consumed")
             params["consumed"] = tool.consumed_quantity
        if tool.trained is not None:
             updates.append("trained = :trained")
             params["trained"] = tool.trained
        
        if not updates:
             return {"success": True, "message": "No changes provided"}

        sql = f"UPDATE tools SET {', '.join(updates)} WHERE tool_id = :id"
        conn.execute(text(sql), params)
        conn.commit()
    
    return {"success": True, "message": "Tool updated successfully"}


@router.put("/tools/{tool_id}/stock-image")
async def upload_tool_stock_image(tool_id: int, file: UploadFile = File(...)):
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    with engine_tools.connect() as conn:
        check = conn.execute(text("SELECT tool_id FROM tools WHERE tool_id = :id"), {"id": tool_id}).fetchone()
        if not check:
            raise HTTPException(status_code=404, detail="Tool not found")

        conn.execute(
            text("UPDATE tools SET image = :image WHERE tool_id = :id"),
            {"id": tool_id, "image": image_bytes},
        )
        conn.commit()

    return {"success": True, "message": "Stock image updated successfully"}
