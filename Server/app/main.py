"""
PURPOSE:
Application entry module for the FastAPI backend. Wires middleware, startup
tasks, CORS policy, and router registration.

API ENDPOINTS OWNED:
- GET /

API ENDPOINTS USED:
- None directly. This module mounts routers that provide API endpoints.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, tools, transactions, ml, analytics, terms
from app.services import ml_service, image_service

app = FastAPI(title="TOOL-E Backend Server (Modular)")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"INCOMING REQUEST: {request.method} {request.url}")
    print(f"PATH HEX: {request.url.path.encode('utf-8').hex()}") # Detect hidden chars
    response = await call_next(request)
    print(f"OUTGOING RESPONSE: {response.status_code}")
    return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    # Allow all origins for development/LAN access
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Events
@app.on_event("startup")
async def startup_event():
    # Load ML Model
    ml_service.load_ml_model()
    
    # Init Paths
    image_service.init_image_dirs()
    
    # Run cleanup
    image_service.cleanup_temp_files(max_age_hours=24)

# Include Routers
app.include_router(auth.router)
app.include_router(tools.router)
app.include_router(transactions.router)
app.include_router(ml.router)
app.include_router(analytics.router)
app.include_router(terms.router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Server is running"}
