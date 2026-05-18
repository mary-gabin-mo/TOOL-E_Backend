"""
PURPOSE:
Handles user validation against Makerspace records and admin web login.

API ENDPOINTS OWNED:
- POST /validate_user
- POST /api/auth/login

"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.models import UserRequest, ValidateUserResponse, UserDetails, LoginPayload, LoginResponse, LoginUser
from app.database import engine_users, engine_tools
import secrets
from datetime import date, timedelta

router = APIRouter()

@router.post("/validate_user", response_model=ValidateUserResponse)
async def validate_user_route(request: UserRequest):
    with engine_users.connect() as conn:
        print(f"[SERVER] Checking User Database...")

        if request.UCID:
            print(f"[SERVER] Validating UserID: {request.UCID}")
            # 0:FirstName, 1:LastName, 2:email, 3:UCID, 4:UNICARDBarcode, 5:recordDate
            sql_query = text(f"SELECT FirstName, LastName, email, UCID, UNICARDBarcode, recordDate FROM MakerspaceCapstone WHERE UCID = :ucid ")
            user = conn.execute(sql_query,{"ucid": int(request.UCID)}).fetchone()
        
        elif request.barcode:
            print(f"[SERVER] Validating UserID: {request.barcode}")
            sql_query = text("SELECT FirstName, LastName, email, UCID, UNICARDBarcode, recordDate FROM MakerspaceCapstone WHERE UNICARDBarcode = :barcode")
            barcode_input = f"{request.barcode};" 
            user = conn.execute(sql_query, {"barcode": barcode_input}).fetchone()
        
        else:
             return ValidateUserResponse(success=False, message="No ID provided")

        if not user:
            return ValidateUserResponse(success=False, message="User not found in database")
        
        first_name = user[0]                
        last_name = user[1]
        email = user[2]
        try:
             found_ucid = int(user[3])
        except (ValueError, TypeError):
             found_ucid = 0
             
        waiver_date = user[5]        

        # Check waiver (recordDate) - must be within 365 days
        one_year_ago = date.today() - timedelta(days=365)
            
        if waiver_date is None or waiver_date < one_year_ago:
            return ValidateUserResponse(success=False, message="Waiver is expired, please renew")
        
        return ValidateUserResponse(
            success=True, 
            # message=f"Access Granted, {first_name}",
            user=UserDetails(
                first_name=first_name,
                last_name=last_name,
                email=email,
                ucid=found_ucid
            )
        )

@router.post("/api/auth/login", response_model=LoginResponse)
async def login(payload: LoginPayload):
    with engine_tools.connect() as conn:
        user = conn.execute(
            text(
                """
                SELECT user_id, user_name, email
                FROM users
                WHERE LOWER(email) = LOWER(:email)
                LIMIT 1
                """
            ),
            {"email": payload.email.strip()},
        ).fetchone()

    if not user or payload.password != str(user.user_id):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = secrets.token_urlsafe(32)

    return LoginResponse(
        token=token,
        user=LoginUser(
            user_id=user.user_id,
            user_name=user.user_name,
            email=user.email,
        ),
    )
