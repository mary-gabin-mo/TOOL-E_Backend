"""
PURPOSE:
Handles transaction listing, creation, batch kiosk submission, updates,
returns, and deletion logic (including inventory adjustments).

API ENDPOINTS OWNED:
- GET /transactions
- GET /transactions/unreturned
- POST /transactions
- POST /transactions/batch
- DELETE /transactions/{transaction_id}
- PUT /transactions/{transaction_id}
- POST /transactions/kiosk

"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from typing import Optional
from datetime import datetime
import uuid
from app.models import TransactionInput, TransactionUpdate, TransactionBatchInput, KioskTransactionRequest
from app.services import image_service
import os
from app.database import engine_tools
# Duplicate import removed
# from app.services import image_service

router = APIRouter()

@router.get("/transactions")#website
async def get_transactions(
    user_id: Optional[int] = None, 
    page: int = 1, 
    limit: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = 'dateOut',
    sort_order: str = 'desc',
    search_term: Optional[str] = None,
    status: Optional[str] = None
):
    offset = (page - 1) * limit
    with engine_tools.connect() as conn:
        conditions = []
        params = {}
        
        if user_id is not None:
            conditions.append("t.user_id = :user_id")
            params["user_id"] = user_id
            
        if start_date:
            conditions.append("t.checkout_timestamp >= :start_date")
            params["start_date"] = start_date
            
        if end_date:
            conditions.append("t.checkout_timestamp < DATE_ADD(:end_date, INTERVAL 1 DAY)")
            params["end_date"] = end_date

        if status:
            status_list = status.split(',')
            status_conditions = []
            for s in status_list:
                s = s.strip()
                if s == 'Returned':
                    status_conditions.append("t.return_timestamp IS NOT NULL")
                elif s == 'Overdue':
                    status_conditions.append("(t.return_timestamp IS NULL AND t.desired_return_date < NOW())")
                elif s == 'Borrowed':
                    status_conditions.append("(t.return_timestamp IS NULL AND (t.desired_return_date >= NOW() OR t.desired_return_date IS NULL))")
            
            if status_conditions:
                conditions.append(f"({' OR '.join(status_conditions)})")

        if search_term:
            conditions.append("(CAST(t.user_id AS CHAR) LIKE :search OR CAST(t.tool_id AS CHAR) LIKE :search OR LOWER(t.purpose) LIKE :search)")
            params["search"] = f"%{search_term.lower()}%"

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        order_clause = "ORDER BY t.checkout_timestamp DESC"
        if sort_by == 'dateOut':
            order_clause = f"ORDER BY t.checkout_timestamp {sort_order.upper()}"
        elif sort_by == 'dateDue':
            order_clause = f"ORDER BY t.desired_return_date {sort_order.upper()}"

        count_sql = f"""
            SELECT COUNT(*) 
            FROM transactions t 
            LEFT JOIN users u ON t.user_id = u.user_id
            LEFT JOIN tools tl ON t.tool_id = tl.tool_id
            {where_clause}
        """
        total = conn.execute(text(count_sql), params).scalar()

        base_sql = f"""
            SELECT t.transaction_id, t.user_id, t.tool_id, t.checkout_timestamp, 
                   t.desired_return_date, t.return_timestamp, t.quantity, t.purpose, 
                   t.image_path, t.return_image_path, t.classification_correct, t.weight,
                   COALESCE(t.user_name, u.user_name) as user_name, tl.tool_name
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.user_id
            LEFT JOIN tools tl ON t.tool_id = tl.tool_id
            {where_clause}
            {order_clause}
        """
        
        if limit > 0:
            base_sql += " LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset
            
        result = conn.execute(text(base_sql), params)
        
        transactions = []
        for row in result:
            status = "Borrowed"
            if row.return_timestamp:
                status = "Returned"
            elif row.desired_return_date and row.desired_return_date < datetime.now():
                status = "Overdue"
            
            transactions.append({
                "transaction_id": row.transaction_id,
                "user_id": row.user_id,
                "user_name": row.user_name,
                "tool_id": row.tool_id,
                "tool_name": row.tool_name,
                "checkout_timestamp": row.checkout_timestamp,
                "desired_return_date": row.desired_return_date,
                "return_timestamp": row.return_timestamp,
                "quantity": row.quantity,
                "purpose": row.purpose,
                "image_path": row.image_path,
                "return_image_path": row.return_image_path,
                "classification_correct": bool(row.classification_correct) if row.classification_correct is not None else None,
                "weight": row.weight,
                "status": status
            })
            
        return {
            "items": transactions,
            "total": total,
            "page": page,
            "size": limit,
            "pages": (total + limit - 1) // limit if limit > 0 else 1
        }

@router.get("/transactions/unreturned")
async def get_unreturned_transactions(user_id: Optional[int] = None):
    """
    Fetches all transactions that have not been returned yet (return_timestamp IS NULL).
    Optionally filters by user_id.
    """
    with engine_tools.connect() as conn:
        query = """
            SELECT t.transaction_id, t.user_id, t.tool_id, t.checkout_timestamp, 
                   t.desired_return_date, t.return_timestamp, t.quantity, t.purpose, 
                   t.image_path, t.return_image_path, t.classification_correct, t.weight,
                   COALESCE(t.user_name, u.user_name) as user_name, tl.tool_name
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.user_id
            LEFT JOIN tools tl ON t.tool_id = tl.tool_id
            WHERE t.return_timestamp IS NULL
        """
        params = {}
        if user_id is not None:
            query += " AND t.user_id = :user_id"
            params["user_id"] = user_id
            
        result = conn.execute(text(query), params)
        
        transactions = []
        for row in result:
            status = "Borrowed"
            if row.desired_return_date and row.desired_return_date < datetime.now():
                status = "Overdue"
                
            transactions.append({
                "transaction_id": row.transaction_id,
                "user_id": row.user_id,
                "user_name": row.user_name,
                "tool_id": row.tool_id,
                "tool_name": row.tool_name,
                "checkout_timestamp": row.checkout_timestamp,
                "desired_return_date": row.desired_return_date,
                "return_timestamp": row.return_timestamp,
                "quantity": row.quantity,
                "purpose": row.purpose,
                "image_path": row.image_path,
                "return_image_path": row.return_image_path,
                "classification_correct": bool(row.classification_correct) if row.classification_correct is not None else None,
                "weight": row.weight,
                "status": status
            })
            
        return {"items": transactions}

@router.post("/transactions")
async def create_transaction(transaction: TransactionInput):
    with engine_tools.connect() as conn:
        _process_single_transaction(conn, transaction)
        conn.commit()

    return {"success": True, "message": "Transaction created successfully"}

@router.post("/transactions/batch")
async def create_transaction_batch(batch: TransactionBatchInput):
    """
    Creates multiple transactions in one atomic operation.
    If any transaction fails, the entire batch is rolled back.
    """
    with engine_tools.begin() as conn: # 'begin()' starts a transaction
        count = 0
        for transaction in batch.transactions:
            try:
                _process_single_transaction(conn, transaction)
                count += 1
            except Exception as e:
                # SQLAlchemy's context manager will auto-rollback on exception
                print(f"[SERVER] Batch Error on item {count}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to process item {count+1}: {str(e)}")
    
    return {"success": True, "message": f"Successfully created {count} transactions"}

def _process_single_transaction(conn, transaction: TransactionInput):
    """Helper to process logic for a single transaction inside an existing connection"""
    
    # --- Handle Image Move Logic ---
    if transaction.image_path:
        # We need the tool name to organize folders
        # Note: image moving is not transactional on the filesystem, 
        # but if DB fails, we just have an orphan file (better than missing file)
        if transaction.tool_id:
              tool_row = conn.execute(text("SELECT tool_name FROM tools WHERE tool_id = :id"), {"id": transaction.tool_id}).fetchone()
              if tool_row:
                  tool_name = tool_row[0]
              else:
                  tool_name = "Other"
        else:
              tool_name = "Other"

        is_correct = transaction.classification_correct if transaction.classification_correct is not None else False
        
        new_path = image_service.move_image_to_permanent(
            filename=transaction.image_path, 
            tool_name=tool_name, 
            classification_correct=is_correct,
            new_transaction_id=transaction.transaction_id or str(uuid.uuid4())
        )
        
        if new_path:
            print(f"[SERVER] Moved image to {new_path}")
            transaction.image_path = new_path
        else:
            print(f"[SERVER] Warning: Image path provided {transaction.image_path} but file not found in temp.")
            transaction.image_path = os.path.basename(transaction.image_path) # Fallback to clean filename

    query = text("""
        INSERT INTO transactions
        (transaction_id, user_id, tool_id, desired_return_date, return_timestamp, quantity, purpose,
            image_path, return_image_path, classification_correct, weight)
        VALUES
        (:transaction_id, :user_id, :tool_id, :desired_return_date, :return_timestamp, :quantity, :purpose,
            :image_path, :return_image_path, :classification_correct, :weight)
    """)
    conn.execute(query, {
        "transaction_id": transaction.transaction_id or str(uuid.uuid4()),
        "user_id": transaction.user_id,
        "tool_id": transaction.tool_id,
        "desired_return_date": transaction.desired_return_date,
        "return_timestamp": transaction.return_timestamp,
        "quantity": transaction.quantity,
        "purpose": transaction.purpose,
        "image_path": transaction.image_path,
        "return_image_path": transaction.return_image_path,
        "classification_correct": transaction.classification_correct,
        "weight": transaction.weight,
    })

@router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str):
    with engine_tools.connect() as conn:
        # Fetch transaction details
        tx = conn.execute(
            text("SELECT transaction_id, tool_id, quantity, return_timestamp FROM transactions WHERE transaction_id = :id"),
            {"id": transaction_id},
        ).fetchone()
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Only restore quantity if not returned
        if tx.return_timestamp is None:
            # Fetch tool type
            tool = conn.execute(
                text("SELECT tool_type FROM tools WHERE tool_id = :tool_id"),
                {"tool_id": tx.tool_id},
            ).fetchone()
            if tool and tool.tool_type == "Borrowable":
                # Increase available_quantity by transaction quantity
                conn.execute(
                    text("UPDATE tools SET available_quantity = available_quantity + :qty WHERE tool_id = :tool_id"),
                    {"qty": tx.quantity, "tool_id": tx.tool_id},
                )

        # Delete the transaction
        conn.execute(
            text("DELETE FROM transactions WHERE transaction_id = :id"),
            {"id": transaction_id},
        )
        conn.commit()

    return {"success": True, "message": "Transaction deleted successfully"}

@router.put("/transactions/{transaction_id}")
async def update_transaction(transaction_id: str, transaction: TransactionUpdate):
    with engine_tools.connect() as conn:
        check = conn.execute(
            text("SELECT transaction_id FROM transactions WHERE transaction_id = :id"),
            {"id": transaction_id},
        ).fetchone()
        if not check:
            raise HTTPException(status_code=404, detail="Transaction not found")

        updates = []
        params = {"id": transaction_id}

        if transaction.user_id is not None:
            updates.append("user_id = :user_id")
            params["user_id"] = transaction.user_id
        if transaction.tool_id is not None:
            updates.append("tool_id = :tool_id")
            params["tool_id"] = transaction.tool_id
        if transaction.desired_return_date is not None:
            updates.append("desired_return_date = :desired_return_date")
            params["desired_return_date"] = transaction.desired_return_date
        if transaction.return_timestamp is not None:
            # Fix ISO format from JS (remove T, Z, milliseconds) for MySQL compatibility
            ts = transaction.return_timestamp
            if 'T' in ts:
                try:
                    # simplistic parsing for '2026-03-03T17:50:01.323Z' -> '2026-03-03 17:50:01'
                    ts = ts.replace('T', ' ').replace('Z', '')
                    if '.' in ts:
                        ts = ts.split('.')[0]
                except Exception:
                    pass
            updates.append("return_timestamp = :return_timestamp")
            params["return_timestamp"] = ts
        if transaction.quantity is not None:
            updates.append("quantity = :quantity")
            params["quantity"] = transaction.quantity
        if transaction.purpose is not None:
            updates.append("purpose = :purpose")
            params["purpose"] = transaction.purpose
        if transaction.image_path is not None:
            updates.append("image_path = :image_path")
            params["image_path"] = transaction.image_path
        if transaction.return_image_path is not None:
            # Return flow: move temp return image to permanent folder and store final filename.
            desired_return_filename = os.path.basename(transaction.return_image_path) if transaction.return_image_path else None
            temp_return_filename = os.path.basename(transaction.temp_img_filename) if transaction.temp_img_filename else desired_return_filename

            if temp_return_filename:
                tool_name_row = conn.execute(
                    text("""
                        SELECT COALESCE(tl.tool_name, 'Other') AS tool_name
                        FROM transactions t
                        LEFT JOIN tools tl ON t.tool_id = tl.tool_id
                        WHERE t.transaction_id = :id
                    """),
                    {"id": transaction_id},
                ).fetchone()

                resolved_tool_name = tool_name_row.tool_name if tool_name_row and tool_name_row.tool_name else "Other"
                is_correct = transaction.classification_correct if transaction.classification_correct is not None else True

                moved_return = image_service.move_image_to_permanent(
                    filename=temp_return_filename,
                    tool_name=resolved_tool_name,
                    classification_correct=is_correct,
                    new_filename=desired_return_filename,
                    new_transaction_id=transaction_id,
                )

                if moved_return:
                    params["return_image_path"] = moved_return
                else:
                    print(f"[SERVER] Warning: Failed to move return image {temp_return_filename} for tx {transaction_id}")
                    params["return_image_path"] = desired_return_filename
            else:
                params["return_image_path"] = desired_return_filename

            updates.append("return_image_path = :return_image_path")
        if transaction.classification_correct is not None:
            updates.append("classification_correct = :classification_correct")
            params["classification_correct"] = transaction.classification_correct
        if transaction.weight is not None:
            updates.append("weight = :weight")
            params["weight"] = transaction.weight

        if not updates:
            return {"success": True, "message": "No changes provided"}

        sql = f"UPDATE transactions SET {', '.join(updates)} WHERE transaction_id = :id"
        conn.execute(text(sql), params)
        conn.commit()

    return {"success": True, "message": "Transaction updated successfully"}

@router.post("/transactions/kiosk")
async def create_kiosk_transaction(transaction: KioskTransactionRequest):
    """
    Handles transaction submission from the Kiosk frontend.
    Complexity Analysis:
    - Tool Lookup: O(N) where N is the number of tools in the transaction. Each lookup is O(1) assuming index on tool_name.
    - Updates/Inserts: O(N) - Insertions and updates are constant time per item.
    - Total Time Complexity: O(N) linear with respect to the number of items being borrowed.
    """
    with engine_tools.begin() as conn: # Start transaction
        # 1. Parse User ID
        try:
            u_id = int(transaction.user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")

        # 2. Process Transactions (Logic to update user table removed as per request)
        for item in transaction.transactions:
            # Find the tool
            # Assuming tool_name is unique or we pick one.
            tool_row = conn.execute(
                text("SELECT tool_id, available_quantity FROM tools WHERE tool_name = :name FOR UPDATE"),
                {"name": item.tool_name}
            ).fetchone()

            if not tool_row:
                print(f"[SERVER] Tool '{item.tool_name}' not found in DB. Creating new custom tool.")
                t_id = None
                
                # Check if it's strictly "Other". If it's a real typed name, insert it in DB.
                if item.tool_name and item.tool_name.lower() != 'other':
                    try:
                        result = conn.execute(
                            text("""
                                INSERT INTO tools (tool_name, tool_type, current_status, total_quantity, available_quantity) 
                                VALUES (:name, :type, :status, :total, :avail)
                            """),
                            {
                                "name": item.tool_name,
                                "type": "Manual Entry",
                                "status": "In Use",
                                "total": 1,
                                "avail": 0
                            }
                        )
                        # Fetch the newly generated ID
                        t_id = result.lastrowid
                        print(f"[SERVER] Created new tool '{item.tool_name}' with ID: {t_id}")
                        
                        # Create folders for it
                        safe_tool_name = "".join([c for c in item.tool_name if c.isalnum() or c in (' ', '-', '_')]).strip()
                        for status_dir in ['Yes', 'No']:
                            os.makedirs(os.path.join(image_service.CAPTURED_IMAGES_DIR, status_dir, safe_tool_name), exist_ok=True)
                            
                    except Exception as e:
                        print(f"[SERVER] Error inserting custom tool: {e}")
            else:
                t_id, avail_qty = tool_row
                if avail_qty <= 0:
                    print(f"[SERVER] Kiosk found unexpected '{item.tool_name}' (avail=0). Incrementing total_quantity by 1.")
                    conn.execute(
                        text("UPDATE tools SET total_quantity = total_quantity + 1, current_status = 'In Use' WHERE tool_id = :tid"),
                        {"tid": t_id}
                    )
                else:
                    # Update Tool Status
                    conn.execute(
                        text("UPDATE tools SET available_quantity = available_quantity - 1, current_status = IF(available_quantity - 1 > 0, 'Available', 'In Use') WHERE tool_id = :tid"),
                        {"tid": t_id}
                    )

            # Move Image to Permanent Storage (if path exists)
            final_img_path = item.img_filename
            if item.img_filename:
                # Attempt to move/organize using the service to keep folders clean
                # We assume correct=True for new transactions unless specified otherwise
                temp_name = os.path.basename(item.temp_img_filename or item.img_filename)
                final_name = os.path.basename(item.img_filename)
                
                # Determine classification correctness (default to True if not provided, or handle None)
                # If item.classification_correct is explicitly False, use False.
                is_correct = True
                if item.classification_correct is not None:
                    is_correct = item.classification_correct

                # If the AI predicted 'Other' or it wasn't found in DB, just organize it as 'Other'
                resolved_tool_name = item.tool_name if item.tool_name and item.tool_name.lower() != 'other' else 'Other'

                # Pass the transaction_id to explicitly rename the file from 'capture_xxx.jpg'
                moved_path = image_service.move_image_to_permanent(
                    filename=temp_name,
                    tool_name=resolved_tool_name, 
                    classification_correct=is_correct, 
                    new_filename=final_name,
                    new_transaction_id=item.transaction_id,
                )
                if moved_path:
                    print(f"[SERVER] Successfully moved and renamed kiosk image to {moved_path}")
                    final_img_path = moved_path
                else:
                    print(f"[SERVER] Warning: Failed to move kiosk image {temp_name}")
                    final_img_path = final_name  # Fallback to payload final filename

            # Log Transaction
            desired_return = None
            if transaction.return_date:
                try:
                    # Parse the incoming date sent from the kiosk
                    desired_return = datetime.strptime(transaction.return_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass # Or handle error

            conn.execute(
                text("""
                    INSERT INTO transactions 
                    (transaction_id, user_id, user_name, tool_id, desired_return_date, checkout_timestamp, image_path, purpose, classification_correct, weight)
                    VALUES (:transaction_id, :uid, :uname, :tid, :d_return, NOW(), :img, :purpose, :class_correct, :weight)
                """),
                {
                    "transaction_id": item.transaction_id,
                    "uid": u_id,
                    "uname": transaction.user_name,
                    "tid": t_id,
                    "d_return": desired_return,
                    "img": final_img_path,
                    "purpose": transaction.purpose or 'Kiosk Borrow',
                    "class_correct": item.classification_correct,
                    "weight": item.weight or 0,
                }
            )

    return {"success": True, "message": "Transaction recorded"}
