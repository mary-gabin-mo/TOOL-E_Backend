"""
PURPOSE:
Loads the trained EfficientNet model and performs image inference.

API ENDPOINTS USED:
- None directly. Called by POST /identify_tool.
"""

import os
import json
import torch
import torch.nn as nn
from torchvision import transforms, models
from torchvision.models import EfficientNet_V2_S_Weights
from PIL import Image

# ==========================================
# ML CONFIGURATION & SETUP
# ==========================================
# Calculate paths relative to the Server root (assuming this file is in app/services)
# We want to go up two levels to get to Server/
BASE_DIR = os.path.dirname((os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'efficientnet_finetuned_v2.pth')
CLASS_NAMES_PATH = os.path.join(BASE_DIR, 'class_names.json')

IMG_SIZE = 384
NORMALIZE_MEAN = [0.485, 0.456, 0.406]
NORMALIZE_STD = [0.229, 0.224, 0.225]

# Load Class Names
CLASS_NAMES = []
if os.path.exists(CLASS_NAMES_PATH):
    try:
        with open(CLASS_NAMES_PATH, 'r') as f:
            CLASS_NAMES = json.load(f)
        print(f"[ML] Loaded {len(CLASS_NAMES)} classes.")
    except Exception as e:
        print(f"[ML] Error loading class names: {e}")
else:
    print(f"[ML] Warning: Class names file not found at {CLASS_NAMES_PATH}")

# Define Transform
inference_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=NORMALIZE_MEAN, std=NORMALIZE_STD)
])

# Load Model Logic
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
ml_model = None

def load_ml_model():
    global ml_model
    if not os.path.exists(MODEL_PATH):
        print(f"[ML] Model file not found at {MODEL_PATH}. ML features disabled.")
        return

    print("[ML] Loading AI Model... (This may take a few seconds)")
    try:
        weights = EfficientNet_V2_S_Weights.DEFAULT
        model = models.efficientnet_v2_s(weights=weights)
        
        # Rebuild Head
        in_features = model.classifier[1].in_features
        # Ensure we have class names to determine output size, default to 15 if missing
        num_classes = len(CLASS_NAMES) if CLASS_NAMES else 15
        model.classifier[1] = nn.Linear(in_features, num_classes)
        
        # Load Weights
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
        model.to(device)
        model.eval()
        ml_model = model
        print("[ML] Model Loaded Successfully!")
    except Exception as e:
        print(f"[ML] Failed to load model: {e}")

def predict_image(image: Image.Image):
    if ml_model is None:
        raise Exception("ML Model is not loaded")

    # Preprocess
    input_tensor = inference_transform(image)
    input_batch = input_tensor.unsqueeze(0).to(device)

    # Predict
    with torch.no_grad():
        output = ml_model(input_batch)
        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        
        # Get top prediction
        top_prob, top_catid = torch.topk(probabilities, 1)
        class_id = top_catid.item()
        score = top_prob.item()
        
        # Safety check if class_id is valid
        if class_id < len(CLASS_NAMES):
            class_name = CLASS_NAMES[class_id]
        else:
            class_name = f"Unknown_Class_{class_id}"
        
        # Get all probabilities
        all_probs = {CLASS_NAMES[i]: prob.item() for i, prob in enumerate(probabilities) if i < len(CLASS_NAMES)}

    return {
        "prediction": class_name,
        "score": score,
        "all_probabilities": all_probs
    }
