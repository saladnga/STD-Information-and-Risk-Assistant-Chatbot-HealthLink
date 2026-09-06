"""
Prediction router for STD symptom analysis.
Provides /predict and /followup endpoints with calibrated probabilities,
top-k predictions, confidence assessment, and follow-up questions.
The actual logic lives in services/prediction_logic.py - this file only
validates requests, calls the model, and shapes the response.
"""

import sys
import os

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from model import (
        process_text_to_feature,
        get_model,
        get_label_encoder,
        get_feature_columns,
    )
except ImportError:
    # Handle import error gracefully
    def process_text_to_feature(*args, **kwargs):
        raise NotImplementedError("Model not available")

    def get_model(*args, **kwargs):
        return None

    def get_label_encoder(*args, **kwargs):
        return None

    def get_feature_columns(*args, **kwargs):
        return []

from services.prediction_logic import (
    TOP_K,
    TEMPERATURE,
    QUESTION_BANK,
    calibrate_probabilities,
    get_top_k_predictions,
    map_question_text_to_feature,
    generate_next_question,
    update_features_from_answer,
)

router = APIRouter(prefix="/predict", tags=["prediction"])

CONFIDENCE_THRESHOLD = 0.7  # If confidence < 0.7, ask follow-up question

# Feature columns that describe the user, not a symptom - never surfaced as
# a "detected symptom" even when present.
NON_SYMPTOM_FEATURES = [
    "age",
    "new_partners_last_3_months",
    "condom_use_consistency_never",
    "condom_use_consistency_sometimes",
]


class SymptomRequest(BaseModel):
    text: str
    top_k: Optional[int] = TOP_K
    confidence_threshold: Optional[float] = CONFIDENCE_THRESHOLD


class FollowupRequest(BaseModel):
    previous_features: Dict[str, int]  # Current feature state
    question_id: Optional[str] = None  # ID of the question being answered
    answer: str  # "yes", "no", or free text
    previous_prediction: Optional[str] = None
    previous_probabilities: Optional[Dict[str, float]] = None
    asked_questions: Optional[List[str]] = []  # List of question IDs already asked


def _require_model():
    """Load model components or raise the standard 503 if untrained."""
    model = get_model()
    label_encoder = get_label_encoder()
    feature_columns = get_feature_columns()
    if not model or not label_encoder or not feature_columns:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please ensure model.joblib exists and restart the server.",
        )
    return model, label_encoder, feature_columns


@router.post("")
async def predict(request: SymptomRequest):
    """
    Accepts a text description of symptoms and returns:
    - Calibrated probabilities for all classes
    - Top-k predictions
    - Confidence score
    - Next question if confidence is below threshold
    - Detected symptoms
    """
    model, label_encoder, feature_columns = _require_model()

    feature_dict = process_text_to_feature(request.text, feature_columns)
    feature_df = pd.DataFrame([feature_dict], columns=feature_columns)

    raw_probs = model.predict_proba(feature_df)[0]
    calibrated_probs = calibrate_probabilities(raw_probs, temperature=TEMPERATURE)
    class_probability = dict(zip(label_encoder.classes_, calibrated_probs.tolist()))

    prediction_class = model.predict(feature_df)[0]
    prediction_class_name = label_encoder.inverse_transform([prediction_class])[0]
    confidence = float(class_probability[prediction_class_name])

    top_k = get_top_k_predictions(class_probability, k=request.top_k)

    detected_symptoms = {
        k: v
        for k, v in feature_dict.items()
        if v == 1 and k not in NON_SYMPTOM_FEATURES
    }

    next_question = None
    if confidence < request.confidence_threshold:
        next_question = generate_next_question(
            top_predictions=top_k,
            current_features=feature_dict,
            disease_probabilities=class_probability,
            asked_questions=[],
            use_eig=True,
            feature_columns=feature_columns,
        )

    return {
        "prediction": prediction_class_name,
        "confidence": confidence * 100,
        "probabilities": {k: float(v) for k, v in class_probability.items()},
        "top_k": top_k,
        "detected_symptoms": detected_symptoms,
        "needs_followup": confidence < request.confidence_threshold,
        "next_question": next_question,
        "current_features": feature_dict,  # Include for followup endpoint
    }


@router.post("/followup")
async def followup(request: FollowupRequest):
    """
    Processes follow-up answer (yes/no or free text) to previous question.
    Updates features based on answer and returns:
    - Updated probabilities
    - Top-k predictions
    - Confidence score
    - Next question if still not confident
    """
    model, label_encoder, feature_columns = _require_model()

    # Reconstruct question metadata from question_id if available
    question_metadata = {}
    if request.question_id:
        parts = request.question_id.split("_")
        if len(parts) >= 3:
            pred1, pred2 = parts[0], parts[1]
            question_metadata = {
                "question_id": request.question_id,
                "disease_pair": [pred1, pred2],
                "feature_target": None,
            }
            if pred1 in QUESTION_BANK and pred2 in QUESTION_BANK[pred1]:
                questions = QUESTION_BANK[pred1][pred2]
                if questions:
                    question_metadata["feature_target"] = (
                        map_question_text_to_feature(questions[0])
                    )

    updated_features = update_features_from_answer(
        request.previous_features, question_metadata, request.answer
    )
    for feature in feature_columns:
        if feature not in updated_features:
            updated_features[feature] = 0

    feature_df = pd.DataFrame([updated_features], columns=feature_columns)

    raw_probs = model.predict_proba(feature_df)[0]
    calibrated_probs = calibrate_probabilities(raw_probs, temperature=TEMPERATURE)
    class_probability = dict(zip(label_encoder.classes_, calibrated_probs.tolist()))

    prediction_class = model.predict(feature_df)[0]
    prediction_class_name = label_encoder.inverse_transform([prediction_class])[0]
    confidence = float(class_probability[prediction_class_name])

    top_k = get_top_k_predictions(class_probability, k=TOP_K)

    prediction_changed = (
        request.previous_prediction is not None
        and prediction_class_name != request.previous_prediction
    )

    confidence_change = 0.0
    if request.previous_probabilities and request.previous_prediction:
        prev_confidence = request.previous_probabilities.get(
            request.previous_prediction, 0.0
        )
        confidence_change = (confidence - prev_confidence) * 100

    asked_questions_list = request.asked_questions or []
    if request.question_id and request.question_id not in asked_questions_list:
        asked_questions_list = asked_questions_list + [request.question_id]

    next_question = None
    if confidence < CONFIDENCE_THRESHOLD:
        next_question = generate_next_question(
            top_predictions=top_k,
            current_features=updated_features,
            disease_probabilities=class_probability,
            asked_questions=asked_questions_list,
            use_eig=True,
            feature_columns=feature_columns,
        )

    return {
        "prediction": prediction_class_name,
        "previous_prediction": request.previous_prediction,
        "confidence": confidence * 100,
        "confidence_change": confidence_change,
        "probabilities": {k: float(v) for k, v in class_probability.items()},
        "top_k": top_k,
        "prediction_changed": prediction_changed,
        "needs_followup": confidence < CONFIDENCE_THRESHOLD,
        "next_question": next_question,
        "updated_features": updated_features,  # Include for next followup
        "asked_questions": asked_questions_list,  # Return updated list
    }
