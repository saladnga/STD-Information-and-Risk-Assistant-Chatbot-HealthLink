"""
Prediction router for STD symptom analysis.
Provides /predict and /followup endpoints with calibrated probabilities,
top-k predictions, confidence assessment, and follow-up questions.
"""
import pandas as pd
import numpy as np
import json
from fastapi import APIRouter, HTTPException, logger
from pydantic import BaseModel
from typing import Dict, List, Optional, Tuple
import sys
import os


# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import model functions
try:
    from app.model import (
        process_text_to_feature, 
        get_model, 
        get_label_encoder, 
        get_feature_columns
    )
    # Load symptom_map directly
    import json
    current_dir_for_map = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    symptom_map_path = os.path.join(current_dir_for_map, "symptom_map.json")
    try:
        with open(symptom_map_path, "r") as f:
            symptom_map = json.load(f)
    except FileNotFoundError:
        symptom_map = {}
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
    symptom_map = {}

try:
    from knowledge_base import STD_KNOWLEDGE
except ImportError:
    STD_KNOWLEDGE = {}

router = APIRouter(prefix="/predict", tags=["prediction"])

# Load question bank and EIG utilities
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
question_bank_path = os.path.join(current_dir, "question_bank.json")
try:
    with open(question_bank_path, "r") as f:
        QUESTION_BANK = json.load(f)
except FileNotFoundError:
    QUESTION_BANK = {}

# Import EIG utilities
try:
    from eig_utils import (
        select_best_feature_for_question,
        compute_eig_for_all_features,
        map_feature_to_question,
        load_symptom_probabilities
    )
    EIG_AVAILABLE = True
except ImportError:
    EIG_AVAILABLE = False
    def select_best_feature_for_question(*args, **kwargs):
        return None
    def compute_eig_for_all_features(*args, **kwargs):
        return []
    def map_feature_to_question(*args, **kwargs):
        return None
    def load_symptom_probabilities():
        return {}

# Configuration
CONFIDENCE_THRESHOLD = 0.7  # If confidence < 0.7, ask follow-up question
TOP_K = 3  # Number of top predictions to return
TEMPERATURE = 1.0  # Temperature for probability calibration (1.0 = no calibration)


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


def calibrate_probabilities(probs: np.ndarray, temperature: float = TEMPERATURE) -> np.ndarray:
    """
    Apply temperature scaling for probability calibration.
    Lower temperature (< 1.0) makes predictions more confident.
    Higher temperature (> 1.0) makes predictions less confident.
    """
    if temperature == 1.0:
        return probs
    
    # Apply temperature scaling
    logits = np.log(probs + 1e-10) / temperature
    exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
    calibrated = exp_logits / np.sum(exp_logits)
    return calibrated


def get_top_k_predictions(
    probabilities: Dict[str, float],
    k: int = TOP_K
) -> List[Dict[str, float]]:
    """
    Get top-k predictions sorted by probability.
    """
    sorted_probs = sorted(
        probabilities.items(),
        key=lambda x: x[1],
        reverse=True
    )[:k]
    
    return [
        {"disease": disease, "probability": float(prob), "confidence": float(prob * 100)}
        for disease, prob in sorted_probs
    ]


def generate_next_question(
    top_predictions: List[Dict[str, float]],
    current_features: Dict[str, int],
    disease_probabilities: Dict[str, float],
    question_bank: Dict = QUESTION_BANK,
    asked_questions: Optional[List[str]] = None,
    use_eig: bool = True,
    feature_columns: Optional[List[str]] = None
) -> Optional[Dict[str, any]]:
    """
    Generate the next follow-up question using EIG (Expected Information Gain) or question bank.
    Returns question text and metadata about which feature it targets.
    
    Args:
        top_predictions: List of top-k predictions
        current_features: Current feature state
        disease_probabilities: Current P(disease) distribution for EIG calculation
        question_bank: Question bank dictionary (fallback)
        asked_questions: List of question IDs that have already been asked
        use_eig: Whether to use EIG for question selection (default: True)
        feature_columns: List of all feature columns
    
    Returns:
        Question dictionary with question text, feature target, and metadata
    """
    if len(top_predictions) < 1:
        return None
    
    if asked_questions is None:
        asked_questions = []
    
    # Try EIG-based question selection first (if available)
    if use_eig and EIG_AVAILABLE:
        # Get top-k diseases for EIG calculation
        top_k_diseases = [pred["disease"] for pred in top_predictions[:3]]
        
        # Select best feature using EIG
        best_feature_result = select_best_feature_for_question(
            disease_probabilities=disease_probabilities,
            current_features=current_features,
            top_k_diseases=top_k_diseases,
            feature_columns=feature_columns
        )
        
        if best_feature_result:
            best_feature, eig_value = best_feature_result
            
            # Skip if we've already asked about this feature
            # (can be enhanced to track by feature name instead of question_id)
            feature_question_id = f"eig_{best_feature}"
            if feature_question_id not in asked_questions:
                # Map feature to question text
                disease_pair = [top_predictions[0]["disease"], top_predictions[1]["disease"]] if len(top_predictions) >= 2 else [top_predictions[0]["disease"]]
                question_text = map_feature_to_question(best_feature, question_bank, disease_pair)
                
                if question_text:
                    return {
                        "question": question_text,
                        "question_id": feature_question_id,
                        "feature_target": best_feature,
                        "expected_answer_type": "yes_no",
                        "disease_pair": disease_pair,
                        "eig_value": float(eig_value),
                        "selection_method": "eig"
                    }
    
    # Fallback to question bank approach
    if len(top_predictions) >= 2:
        pred1 = top_predictions[0]["disease"]
        pred2 = top_predictions[1]["disease"]
        
        # Check if we have questions for this disease pair
        if pred1 in question_bank and pred2 in question_bank[pred1]:
            disease_pair_questions = question_bank[pred1][pred2]
            
            # Check if new structure (feature-keyed) or old structure (array)
            if isinstance(disease_pair_questions, dict):
                # New structure: questions grouped by feature
                # Iterate through features and find unasked questions
                for feature_key, questions in disease_pair_questions.items():
                    if not isinstance(questions, list):
                        continue
                    
                    for idx, question_text in enumerate(questions):
                        question_id = f"{pred1}_{pred2}_{feature_key}_{idx}"
                        
                        # Skip if already asked
                        if question_id in asked_questions:
                            continue
                        
                        # Return question with feature target
                        return {
                            "question": question_text,
                            "question_id": question_id,
                            "feature_target": feature_key,
                            "expected_answer_type": "yes_no",
                            "disease_pair": [pred1, pred2],
                            "selection_method": "question_bank"
                        }
            else:
                # Old structure: array of questions (backward compatibility)
                questions = disease_pair_questions
                if questions:
                    # Find the first question that hasn't been asked
                    for idx, question_text in enumerate(questions):
                        question_id = f"{pred1}_{pred2}_{idx}"
                        
                        # Skip if already asked
                        if question_id in asked_questions:
                            continue
                        
                        # Determine feature target
                        question_lower = question_text.lower()
                        feature_target = None
                        
                        # Map common question patterns to features
                        if "fishy" in question_lower or "odor" in question_lower:
                            feature_target = "odor_fishy"
                        elif "discharge" in question_lower:
                            if "thick" in question_lower or "yellow" in question_lower or "green" in question_lower:
                                feature_target = "discharge_thick"
                            elif "thin" in question_lower:
                                feature_target = "discharge_thin"
                        elif "itching" in question_lower or "itch" in question_lower:
                            feature_target = "itching"
                        elif "pain" in question_lower and "abdominal" in question_lower:
                            feature_target = "abdominal_pain"
                        elif "spotting" in question_lower or "bleeding" in question_lower:
                            feature_target = "spotting"
                        elif "sore throat" in question_lower:
                            feature_target = "sore_throat"
                        elif "fever" in question_lower:
                            feature_target = "fever"
                        elif "sores" in question_lower or "ulcers" in question_lower or "blisters" in question_lower:
                            if "painless" in question_lower:
                                feature_target = "ulcer_painless"
                            else:
                                feature_target = "ulcers_painful"
                        
                        # Return the first unasked question
                        return {
                            "question": question_text,
                            "question_id": question_id,
                            "feature_target": feature_target,
                            "expected_answer_type": "yes_no",
                            "disease_pair": [pred1, pred2],
                            "selection_method": "question_bank"
                        }
    
    return None


def update_features_from_answer(
    current_features: Dict[str, int],
    question_metadata: Dict[str, any],
    answer: str
) -> Dict[str, int]:
    """
    Update features based on yes/no answer to a question.
    """
    updated_features = current_features.copy()
    answer_lower = answer.lower().strip()
    
    # Check if answer is yes/no
    is_yes = answer_lower in ["yes", "y", "true", "1", "affirmative", "correct"]
    is_no = answer_lower in ["no", "n", "false", "0", "negative", "incorrect"]
    
    if not (is_yes or is_no):
        # If not a clear yes/no, try to extract features from free text using regex-based matching
        # Use the same process_text_to_feature function for symptom extraction
        try:
            feature_columns = get_feature_columns()
            if feature_columns:
                extracted_features = process_text_to_feature(answer, feature_columns)
                # Update features with any new symptoms detected in the answer
                for key, value in extracted_features.items():
                    if value == 1 and key not in ["age", "new_partners_last_3_months", 
                                                   "condom_use_consistency_never", 
                                                   "condom_use_consistency_sometimes"]:
                        updated_features[key] = 1
        except Exception as e:
            logger.warning(f"Could not extract features from free text answer: {e}")
            # Continue with yes/no interpretation as fallback
            is_yes = True if any(word in answer_lower for word in ["yes", "y", "have", "do", "does", "am", "is", "are"]) else False
            is_no = True if any(word in answer_lower for word in ["no", "n", "not", "don't", "doesn't", "never", "none"]) else False
    
    # Update feature based on question metadata
    feature_target = question_metadata.get("feature_target")
    if feature_target and feature_target in updated_features:
        if is_yes:
            updated_features[feature_target] = 1
        elif is_no:
            updated_features[feature_target] = 0
    
    return updated_features


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
    model = get_model()
    label_encoder = get_label_encoder()
    model_feature_column = get_feature_columns()
    
    if model is None or label_encoder is None or model_feature_column is None or not model_feature_column:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please ensure model.joblib exists and restart the server."
        )

    # Convert text to feature vector
    feature_dict = process_text_to_feature(request.text, model_feature_column)
    
    # Ensure features are in the exact order matching training data (1:1 match required)
    # Create DataFrame with features in exact training order
    feature_df = pd.DataFrame([feature_dict], columns=model_feature_column)
    
    # Verify all features are present and fill missing with 0
    missing_cols = set(model_feature_column) - set(feature_df.columns)
    if missing_cols:
        for col in missing_cols:
            feature_df[col] = 0
        # Ensure exact order - reorder columns to match training order exactly
        feature_df = feature_df[model_feature_column]
    
    # Final validation: ensure feature order matches training exactly
    if list(feature_df.columns) != model_feature_column:
        raise HTTPException(
            status_code=500,
            detail="Critical error: Feature order does not match training order. Cannot proceed with inference."
        )

    # Get raw probabilities
    raw_probs = model.predict_proba(feature_df)[0]
    
    # Calibrate probabilities
    calibrated_probs = calibrate_probabilities(raw_probs, temperature=TEMPERATURE)
    
    # Map to class names
    class_probability = dict(
        zip(label_encoder.classes_, calibrated_probs.tolist())
    )
    
    # Get top prediction
    prediction_class = model.predict(feature_df)[0]
    prediction_class_name = label_encoder.inverse_transform([prediction_class])[0]
    confidence = float(class_probability[prediction_class_name])
    
    # Get top-k predictions
    top_k = get_top_k_predictions(class_probability, k=request.top_k)
    
    # Extract only active symptoms (features = 1)
    detected_symptoms = {
        k: v
        for k, v in feature_dict.items()
        if v == 1
        and k not in [
            "age",
            "new_partners_last_3_months",
            "condom_use_consistency_never",
            "condom_use_consistency_sometimes",
        ]
    }
    
    # Generate next question if confidence is below threshold (using EIG)
    next_question = None
    if confidence < request.confidence_threshold:
        next_question = generate_next_question(
            top_predictions=top_k,
            current_features=feature_dict,
            disease_probabilities=class_probability,
            asked_questions=[],
            use_eig=True,
            feature_columns=model_feature_column
        )
    
    return {
        "prediction": prediction_class_name,
        "confidence": confidence * 100,
        "probabilities": {k: float(v) for k, v in class_probability.items()},
        "top_k": top_k,
        "detected_symptoms": detected_symptoms,
        "needs_followup": confidence < request.confidence_threshold,
        "next_question": next_question,
        "current_features": feature_dict  # Include for followup endpoint
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
    model = get_model()
    label_encoder = get_label_encoder()
    model_feature_column = get_feature_columns()
    
    if model is None or label_encoder is None or model_feature_column is None or not model_feature_column:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please ensure model.joblib exists and restart the server."
        )
    
    # Reconstruct question metadata from question_id if available
    question_metadata = {}
    if request.question_id:
        # Parse question_id to extract disease pair
        parts = request.question_id.split("_")
        if len(parts) >= 3:
            pred1 = parts[0]
            pred2 = parts[1]
            question_metadata = {
                "question_id": request.question_id,
                "disease_pair": [pred1, pred2],
                "feature_target": None  # Will be determined from question bank
            }
            # Try to get feature target from question bank
            if pred1 in QUESTION_BANK and pred2 in QUESTION_BANK[pred1]:
                questions = QUESTION_BANK[pred1][pred2]
                if questions:
                    question_text = questions[0]
                    question_lower = question_text.lower()
                    # Map to feature (same logic as generate_next_question)
                    if "fishy" in question_lower or "odor" in question_lower:
                        question_metadata["feature_target"] = "odor_fishy"
                    elif "discharge" in question_lower:
                        if "thick" in question_lower or "yellow" in question_lower or "green" in question_lower:
                            question_metadata["feature_target"] = "discharge_thick"
                        elif "thin" in question_lower:
                            question_metadata["feature_target"] = "discharge_thin"
                    elif "itching" in question_lower or "itch" in question_lower:
                        question_metadata["feature_target"] = "itching"
                    elif "pain" in question_lower and "abdominal" in question_lower:
                        question_metadata["feature_target"] = "abdominal_pain"
                    elif "spotting" in question_lower or "bleeding" in question_lower:
                        question_metadata["feature_target"] = "spotting"
                    elif "sores" in question_lower or "ulcers" in question_lower:
                        if "painless" in question_lower:
                            question_metadata["feature_target"] = "ulcer_painless"
                        else:
                            question_metadata["feature_target"] = "ulcers_painful"
    
    # Update features based on answer
    updated_features = update_features_from_answer(
        request.previous_features,
        question_metadata,
        request.answer
    )
    
    # Ensure all features are present and in exact training order
    for feature in model_feature_column:
        if feature not in updated_features:
            updated_features[feature] = 0
    
    # Create feature dataframe with features in exact training order (1:1 match)
    # This is critical - feature order must match training exactly
    feature_df = pd.DataFrame([updated_features], columns=model_feature_column)
    
    # Validate feature order (additional safety check)
    if list(feature_df.columns) != model_feature_column:
        raise HTTPException(
            status_code=500,
            detail=f"Feature order mismatch: expected {len(model_feature_column)} features in exact order"
        )
    
    # Get updated predictions
    raw_probs = model.predict_proba(feature_df)[0]
    calibrated_probs = calibrate_probabilities(raw_probs, temperature=TEMPERATURE)
    
    class_probability = dict(
        zip(label_encoder.classes_, calibrated_probs.tolist())
    )
    
    # Get top prediction
    prediction_class = model.predict(feature_df)[0]
    prediction_class_name = label_encoder.inverse_transform([prediction_class])[0]
    confidence = float(class_probability[prediction_class_name])
    
    # Get top-k predictions
    top_k = get_top_k_predictions(class_probability, k=TOP_K)
    
    # Check if prediction changed
    prediction_changed = False
    if request.previous_prediction:
        prediction_changed = prediction_class_name != request.previous_prediction
    
    # Calculate confidence change
    confidence_change = 0.0
    if request.previous_probabilities and request.previous_prediction:
        prev_confidence = request.previous_probabilities.get(request.previous_prediction, 0.0)
        confidence_change = (confidence - prev_confidence) * 100
    
    # Generate next question if still not confident
    next_question = None
    asked_questions_list = request.asked_questions or []
    if request.question_id and request.question_id not in asked_questions_list:
        asked_questions_list = asked_questions_list + [request.question_id]
    
    if confidence < CONFIDENCE_THRESHOLD:
        next_question = generate_next_question(
            top_predictions=top_k,
            current_features=updated_features,
            disease_probabilities=class_probability,
            asked_questions=asked_questions_list,
            use_eig=True,
            feature_columns=model_feature_column
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
        "asked_questions": asked_questions_list  # Return updated list
    }
