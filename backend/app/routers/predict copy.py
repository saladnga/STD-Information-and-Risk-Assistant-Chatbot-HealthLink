import pandas as pd
import os
import json
import spacy
from spacy.language import Language
import medspacy
from medspacy.target_matcher import TargetMatcher
from pydantic import BaseModel
from fastapi import APIRouter
from fastapi import Request
from routers.utils import process_text_to_feature, model_feature_column

# Load symptom mapping and rules
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(current_dir, "symptom_target_rules.json"), "r") as f:
    symptom_target_rules = json.load(f)
with open(os.path.join(current_dir, "symptom_map.json"), "r") as x:
    symptom_map = json.load(x)

router = APIRouter(prefix="/predict", tags=["ML Prediction"])

# Global to load in lifespan
model = None
nlp = None
label_encoder = None

# Pydantic Request Models
class SymptomRequest(BaseModel):
    text: str  # Request body for /predict endpoint

# Predict STD based on symptom text
@router.post("/")
async def predict(request:Request, symptom_request: SymptomRequest):
    """
    Accepts a text description of symptoms and returns:
    - Predicted disease label
    - Class probabilities
    - Detected symptom features
    """
    
    model = request.app.state.model
    nlp = request.app.state.nlp
    label_encoder = request.app.state.label_encoder

    # Convert text to feature vector
    feature_dict = process_text_to_feature(symptom_request.text, model_feature_column, nlp)
    feature_df = pd.DataFrame([feature_dict], columns=model_feature_column)

    # Model prediction and probability mapping
    prediction_probability = model.predict_proba(feature_df)
    prediction_class = model.predict(feature_df)
    prediction_class_name = label_encoder.inverse_transform(prediction_class)[0]
    class_probability = dict(
        zip(label_encoder.classes_, prediction_probability[0].tolist())
    )

    # Extract only active symptoms (features = 1)
    return {
        "prediction": prediction_class_name,
        "probabilities": class_probability,
        "detected_symptoms": {
            k: v
            for k, v in feature_dict.items()
            if v == 1
            and k
            not in [
                "age",
                "new_partners_last_3_months",
                "condom_use_consistency_never",
                "condom_use_consistency_sometimes",
            ]
        },
    }
