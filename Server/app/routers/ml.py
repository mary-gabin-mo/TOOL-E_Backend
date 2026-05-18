"""
PURPOSE:
Exposes ML image-classification endpoint used by kiosk and debug UI.

API ENDPOINTS OWNED:
- POST /identify_tool

"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services import ml_service, image_service
from PIL import Image
import io

router = APIRouter()

@router.post("/identify_tool")
async def identify_tool(file: UploadFile = File(...)):
    """
    Receives an image file, runs it through the loaded ML model, 
    and returns the predicted tool class and classification score.
    The kiosk controls the temp filename; this endpoint only returns prediction data.
    """
    try:
        # 1. Read the file content
        contents = await file.read()
        
        # 2. Save temp image exactly as named by kiosk
        image_service.save_temp_image(contents, file.filename)
        
        # 3. Predict
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        result = ml_service.predict_image(image)
        
        result["success"] = True
        return result

    except Exception as e:
        print(f"[ML] Prediction Error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
