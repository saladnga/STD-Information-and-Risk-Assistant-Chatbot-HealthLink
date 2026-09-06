"""
Pure logic for the /predict and /predict/followup endpoints: probability calibration, top-k ranking, and picking the next follow-up question (via
Expected Information Gain, falling back to a static question bank). Kept separate from routers/predict.py so the router only has to wire HTTP requests to these steps.
"""

import os
import json
import logging
from typing import Dict, List, Optional

import numpy as np

from model import process_text_to_feature, get_feature_columns

logger = logging.getLogger(__name__)

TOP_K = 3  # Number of top predictions to return
TEMPERATURE = 1.0  # Temperature for probability calibration (1.0 = no calibration)

# Load question bank (fallback question source when EIG can't pick one)
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
question_bank_path = os.path.join(current_dir, "question_bank.json")
try:
    with open(question_bank_path, "r") as f:
        QUESTION_BANK = json.load(f)
except FileNotFoundError:
    QUESTION_BANK = {}

try:
    from eig_utils import select_best_feature_for_question, map_feature_to_question

    EIG_AVAILABLE = True
except ImportError:
    EIG_AVAILABLE = False

    def select_best_feature_for_question(*args, **kwargs):
        return None

    def map_feature_to_question(*args, **kwargs):
        return None


def calibrate_probabilities(
    probs: np.ndarray, temperature: float = TEMPERATURE
) -> np.ndarray:
    """
    Apply temperature scaling for probability calibration.
    Lower temperature (< 1.0) makes predictions more confident.
    Higher temperature (> 1.0) makes predictions less confident.
    """
    if temperature == 1.0:
        return probs

    logits = np.log(probs + 1e-10) / temperature
    exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
    calibrated = exp_logits / np.sum(exp_logits)
    return calibrated


def get_top_k_predictions(
    probabilities: Dict[str, float], k: int = TOP_K
) -> List[Dict[str, float]]:
    """Get top-k predictions sorted by probability."""
    sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)[:k]
    return [
        {
            "disease": disease,
            "probability": float(prob),
            "confidence": float(prob * 100),
        }
        for disease, prob in sorted_probs
    ]


def map_question_text_to_feature(question_text: str) -> Optional[str]:
    question_lower = question_text.lower()

    if "fishy" in question_lower or "odor" in question_lower:
        return "odor_fishy"
    if "discharge" in question_lower:
        if (
            "thick" in question_lower
            or "yellow" in question_lower
            or "green" in question_lower
        ):
            return "discharge_thick"
        if "thin" in question_lower:
            return "discharge_thin"
        return None
    if "itching" in question_lower or "itch" in question_lower:
        return "itching"
    if "pain" in question_lower and "abdominal" in question_lower:
        return "abdominal_pain"
    if "spotting" in question_lower or "bleeding" in question_lower:
        return "spotting"
    if "sore throat" in question_lower:
        return "sore_throat"
    if "fever" in question_lower:
        return "fever"
    if (
        "sores" in question_lower
        or "ulcers" in question_lower
        or "blisters" in question_lower
    ):
        return "ulcer_painless" if "painless" in question_lower else "ulcers_painful"

    return None


def generate_next_question(
    top_predictions: List[Dict[str, float]],
    current_features: Dict[str, int],
    disease_probabilities: Dict[str, float],
    question_bank: Dict = QUESTION_BANK,
    asked_questions: Optional[List[str]] = None,
    use_eig: bool = True,
    feature_columns: Optional[List[str]] = None,
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
        top_k_diseases = [pred["disease"] for pred in top_predictions[:3]]

        best_feature_result = select_best_feature_for_question(
            disease_probabilities=disease_probabilities,
            current_features=current_features,
            top_k_diseases=top_k_diseases,
            feature_columns=feature_columns,
        )

        if best_feature_result:
            best_feature, eig_value = best_feature_result

            feature_question_id = f"eig_{best_feature}"
            if feature_question_id not in asked_questions:
                disease_pair = (
                    [top_predictions[0]["disease"], top_predictions[1]["disease"]]
                    if len(top_predictions) >= 2
                    else [top_predictions[0]["disease"]]
                )
                question_text = map_feature_to_question(
                    best_feature, question_bank, disease_pair
                )

                if question_text:
                    return {
                        "question": question_text,
                        "question_id": feature_question_id,
                        "feature_target": best_feature,
                        "expected_answer_type": "yes_no",
                        "disease_pair": disease_pair,
                        "eig_value": float(eig_value),
                        "selection_method": "eig",
                    }

    # Fallback to question bank approach
    if len(top_predictions) >= 2:
        pred1 = top_predictions[0]["disease"]
        pred2 = top_predictions[1]["disease"]

        if pred1 in question_bank and pred2 in question_bank[pred1]:
            disease_pair_questions = question_bank[pred1][pred2]

            if isinstance(disease_pair_questions, dict):
                # New structure: questions grouped by feature
                for feature_key, questions in disease_pair_questions.items():
                    if not isinstance(questions, list):
                        continue

                    for idx, question_text in enumerate(questions):
                        question_id = f"{pred1}_{pred2}_{feature_key}_{idx}"
                        if question_id in asked_questions:
                            continue

                        return {
                            "question": question_text,
                            "question_id": question_id,
                            "feature_target": feature_key,
                            "expected_answer_type": "yes_no",
                            "disease_pair": [pred1, pred2],
                            "selection_method": "question_bank",
                        }
            else:
                # Old structure: array of questions (backward compatibility)
                questions = disease_pair_questions
                for idx, question_text in enumerate(questions):
                    question_id = f"{pred1}_{pred2}_{idx}"
                    if question_id in asked_questions:
                        continue

                    feature_target = map_question_text_to_feature(question_text)
                    return {
                        "question": question_text,
                        "question_id": question_id,
                        "feature_target": feature_target,
                        "expected_answer_type": "yes_no",
                        "disease_pair": [pred1, pred2],
                        "selection_method": "question_bank",
                    }

    return None


def update_features_from_answer(
    current_features: Dict[str, int], question_metadata: Dict[str, any], answer: str
) -> Dict[str, int]:
    """Update features based on a yes/no (or free-text) answer to a question."""
    updated_features = current_features.copy()
    answer_lower = answer.lower().strip()

    is_yes = answer_lower in ["yes", "y", "true", "1", "affirmative", "correct"]
    is_no = answer_lower in ["no", "n", "false", "0", "negative", "incorrect"]

    if not (is_yes or is_no):
        # Not a clear yes/no - try to extract features from free text, same
        # regex-based matching used for the initial symptom description.
        try:
            feature_columns = get_feature_columns()
            if feature_columns:
                extracted_features = process_text_to_feature(answer, feature_columns)
                for key, value in extracted_features.items():
                    if value == 1 and key not in [
                        "age",
                        "new_partners_last_3_months",
                        "condom_use_consistency_never",
                        "condom_use_consistency_sometimes",
                    ]:
                        updated_features[key] = 1
        except Exception as e:
            logger.warning(f"Could not extract features from free text answer: {e}")
            is_yes = any(
                word in answer_lower
                for word in ["yes", "y", "have", "do", "does", "am", "is", "are"]
            )
            is_no = any(
                word in answer_lower
                for word in ["no", "n", "not", "don't", "doesn't", "never", "none"]
            )

    feature_target = question_metadata.get("feature_target")
    if feature_target and feature_target in updated_features:
        if is_yes:
            updated_features[feature_target] = 1
        elif is_no:
            updated_features[feature_target] = 0

    return updated_features
