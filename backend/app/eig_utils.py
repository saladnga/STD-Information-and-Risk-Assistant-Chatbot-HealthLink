"""
Expected Information Gain (EIG) utilities for selecting optimal follow-up questions.
Uses P(symptom=1|disease) probabilities to compute EIG for each symptom feature.
"""
import json
import os
import numpy as np
from typing import Dict, List, Optional, Tuple
import math


# Load symptom probabilities
current_dir = os.path.dirname(os.path.abspath(__file__))
symptom_probs_path = os.path.join(current_dir, "symptom_probabilities.json")

# Load symptom probabilities (fallback to empty dict if not available)
_symptom_probs = None


def load_symptom_probabilities() -> Dict:
    """Load P(symptom=1|disease) probabilities from file."""
    global _symptom_probs
    if _symptom_probs is None:
        try:
            if os.path.exists(symptom_probs_path):
                with open(symptom_probs_path, "r") as f:
                    data = json.load(f)
                    _symptom_probs = data.get("probabilities", {})
            else:
                # Fallback: return empty dict
                _symptom_probs = {}
        except Exception as e:
            print(f"Warning: Could not load symptom probabilities: {e}")
            _symptom_probs = {}
    return _symptom_probs


def entropy(probabilities: List[float]) -> float:
    """
    Calculate entropy H(X) = -Sum P(x) * log2(P(x)).
    
    Args:
        probabilities: List of probabilities (should sum to 1)
    
    Returns:
        Entropy value in bits
    """
    # Filter out zero probabilities and normalize
    probs = [p for p in probabilities if p > 0]
    if not probs:
        return 0.0
    
    # Normalize to ensure they sum to 1
    total = sum(probs)
    if total == 0:
        return 0.0
    
    probs = [p / total for p in probs]
    
    # Calculate entropy
    entropy_val = -sum(p * math.log2(p) for p in probs if p > 0)
    return entropy_val


def compute_eig_for_feature(
    feature: str,
    disease_probabilities: Dict[str, float],
    symptom_probs: Optional[Dict] = None
) -> float:
    """
    Compute Expected Information Gain (EIG) for a symptom feature.
    
    EIG(feature) = H(disease) - E[H(disease|feature)]
    
    Where:
    - H(disease) = entropy of current disease distribution
    - E[H(disease|feature)] = expected entropy after observing feature value
    
    Args:
        feature: Symptom feature name (e.g., "dysuria")
        disease_probabilities: Current P(disease) distribution
        symptom_probs: P(symptom=1|disease) probabilities
    
    Returns:
        Expected Information Gain (higher = more informative)
    """
    if symptom_probs is None:
        symptom_probs = load_symptom_probabilities()
    
    if not symptom_probs:
        return 0.0
    
    # Get current entropy H(disease)
    disease_probs = list(disease_probabilities.values())
    current_entropy = entropy(disease_probs)
    
    if current_entropy == 0:
        return 0.0  # No uncertainty, no information gain
    
    # Compute P(feature=1) and P(feature=0)
    p_feature_1 = 0.0
    p_feature_0 = 0.0
    
    for disease, p_disease in disease_probabilities.items():
        if disease in symptom_probs and feature in symptom_probs[disease]:
            p_symptom_given_disease = symptom_probs[disease][feature]
            p_feature_1 += p_disease * p_symptom_given_disease
            p_feature_0 += p_disease * (1 - p_symptom_given_disease)
    
    # Normalize
    total = p_feature_1 + p_feature_0
    if total == 0:
        return 0.0
    
    p_feature_1 /= total
    p_feature_0 /= total
    
    # Compute conditional probabilities P(disease|feature=1) and P(disease|feature=0)
    disease_given_feature_1 = {}
    disease_given_feature_0 = {}
    
    for disease, p_disease in disease_probabilities.items():
        if disease in symptom_probs and feature in symptom_probs[disease]:
            p_symptom_given_disease = symptom_probs[disease][feature]
            
            # P(disease|feature=1) = P(feature=1|disease) * P(disease) / P(feature=1)
            if p_feature_1 > 0:
                disease_given_feature_1[disease] = (p_symptom_given_disease * p_disease) / p_feature_1
            else:
                disease_given_feature_1[disease] = 0.0
            
            # P(disease|feature=0) = P(feature=0|disease) * P(disease) / P(feature=0)
            if p_feature_0 > 0:
                disease_given_feature_0[disease] = ((1 - p_symptom_given_disease) * p_disease) / p_feature_0
            else:
                disease_given_feature_0[disease] = 0.0
        else:
            disease_given_feature_1[disease] = 0.0
            disease_given_feature_0[disease] = 0.0
    
    # Compute expected entropy after observing feature
    entropy_feature_1 = entropy(list(disease_given_feature_1.values()))
    entropy_feature_0 = entropy(list(disease_given_feature_0.values()))
    expected_entropy = p_feature_1 * entropy_feature_1 + p_feature_0 * entropy_feature_0
    
    # Information gain = reduction in entropy
    eig = current_entropy - expected_entropy
    
    return max(0.0, eig)  # Ensure non-negative


def compute_eig_for_all_features(
    disease_probabilities: Dict[str, float],
    current_features: Dict[str, int],
    symptom_probs: Optional[Dict] = None,
    feature_columns: Optional[List[str]] = None
) -> List[Tuple[str, float]]:
    """
    Compute EIG for all symptom features.
    
    Args:
        disease_probabilities: Current P(disease) distribution
        current_features: Current feature state (to skip already known features)
        symptom_probs: P(symptom=1|disease) probabilities
        feature_columns: List of all feature columns (to filter non-symptom features)
    
    Returns:
        List of (feature, eig) tuples sorted by EIG (highest first)
    """
    if symptom_probs is None:
        symptom_probs = load_symptom_probabilities()
    
    if not symptom_probs:
        return []
    
    # Filter out non-symptom features
    non_symptom_features = {
        "age", "new_partners_last_3_months", 
        "condom_use_consistency_never", "condom_use_consistency_sometimes",
        "ground_truth"  # Also exclude label column if present
    }
    
    # Get all symptom features from probabilities
    all_features = set()
    for disease_probs in symptom_probs.values():
        all_features.update(disease_probs.keys())
    
    # Filter to only symptom features
    symptom_features = [f for f in all_features if f not in non_symptom_features]
    
    # If feature_columns provided, use intersection
    if feature_columns:
        symptom_features = [f for f in symptom_features if f in feature_columns]
    
    # Compute EIG for each feature
    feature_eig = []
    for feature in symptom_features:
        # Skip if feature is already known and set (optional - can still ask for confirmation)
        # Skip features that are not in the probabilities data
        if feature not in all_features:
            continue
        
        # Compute EIG
        try:
            eig = compute_eig_for_feature(feature, disease_probabilities, symptom_probs)
            if eig > 0:  # Only include features with positive EIG
                feature_eig.append((feature, eig))
        except Exception as e:
            # Skip features that cause errors in EIG calculation
            continue
    
    # Sort by EIG (highest first)
    feature_eig.sort(key=lambda x: x[1], reverse=True)
    
    return feature_eig


def select_best_feature_for_question(
    disease_probabilities: Dict[str, float],
    current_features: Dict[str, int],
    top_k_diseases: Optional[List[str]] = None,
    symptom_probs: Optional[Dict] = None,
    feature_columns: Optional[List[str]] = None
) -> Optional[Tuple[str, float]]:
    """
    Select the best symptom feature to ask about based on EIG.
    
    Args:
        disease_probabilities: Current P(disease) distribution
        current_features: Current feature state
        top_k_diseases: Optional list of top-k diseases to focus on (for efficiency)
        symptom_probs: P(symptom=1|disease) probabilities
        feature_columns: List of all feature columns
    
    Returns:
        Tuple of (best_feature, eig_value) or None if no features available
    """
    # If top_k_diseases provided, filter probabilities
    if top_k_diseases:
        filtered_probs = {d: disease_probabilities.get(d, 0.0) for d in top_k_diseases}
        # Renormalize
        total = sum(filtered_probs.values())
        if total > 0:
            filtered_probs = {d: p / total for d, p in filtered_probs.items()}
        disease_probabilities = filtered_probs
    
    # Compute EIG for all features
    feature_eig = compute_eig_for_all_features(
        disease_probabilities,
        current_features,
        symptom_probs,
        feature_columns
    )
    
    if not feature_eig:
        return None
    
    # Return the feature with highest EIG
    return feature_eig[0]


def map_feature_to_question(
    feature: str,
    question_bank: Dict,
    disease_pair: Optional[List[str]] = None
) -> Optional[str]:
    """
    Map a feature to an appropriate question text.
    
    Args:
        feature: Feature name (e.g., "dysuria")
        question_bank: Question bank dictionary
        disease_pair: Optional disease pair for context-specific questions
    
    Returns:
        Question text or None
    """
    # Feature to question mapping
    feature_questions = {
        "dysuria": "Do you experience burning or pain when urinating?",
        "discharge_thin": "Do you have thin, clear, or white discharge?",
        "discharge_thick": "Do you have thick discharge?",
        "discharge_yellow_green": "Do you have yellow or green discharge?",
        "odor_fishy": "Do you notice a fishy or unusual odor?",
        "itching": "Do you experience itching or irritation?",
        "abdominal_pain": "Do you have abdominal or lower stomach pain?",
        "pelvic_pain": "Do you experience pelvic pain?",
        "spotting": "Have you noticed any spotting or bleeding between periods?",
        "ulcers_painful": "Do you have painful sores or blisters?",
        "ulcer_painless": "Do you have any painless sores or ulcers?",
        "urinary_frequency": "Do you urinate more frequently than usual?",
        "urinary_urgency": "Do you feel an urgent need to urinate?",
        "fever": "Do you have a fever?",
        "sore_throat": "Do you have a sore throat?",
        "fatigue": "Are you experiencing fatigue or tiredness?",
        "weight_loss": "Have you experienced unexplained weight loss?",
        "swollen_lymph_nodes": "Do you have swollen lymph nodes?",
        "jaundice": "Have you noticed any yellowing of your skin or eyes?",
        "rash_palm_sole": "Do you have a rash on your palms or soles?",
        "blisters_genital": "Do you have blisters in the genital area?",
        "is_asymptomatic": "Are you experiencing any symptoms at all?"
    }
    
    # Try feature-specific question first
    if feature in feature_questions:
        return feature_questions[feature]
    
    # Try disease-pair specific question from question bank
    if disease_pair and len(disease_pair) >= 2:
        pred1, pred2 = disease_pair[0], disease_pair[1]
        if pred1 in question_bank and pred2 in question_bank[pred1]:
            disease_pair_questions = question_bank[pred1][pred2]
            
            # Check if new structure (feature-keyed) or old structure (array)
            if isinstance(disease_pair_questions, dict):
                # New structure: questions grouped by feature
                if feature in disease_pair_questions:
                    questions = disease_pair_questions[feature]
                    if questions and len(questions) > 0:
                        # Return first question for this feature
                        return questions[0] if isinstance(questions, list) else questions
            else:
                # Old structure: array of questions
                questions = disease_pair_questions
                # Try to find a question that matches the feature
                for question in questions:
                    question_lower = question.lower()
                    if feature in question_lower or any(keyword in question_lower for keyword in feature.split("_")):
                        return question
                # Return first question if no match
                if questions and len(questions) > 0:
                    return questions[0]
    
    # Fallback: generic question
    feature_readable = feature.replace("_", " ").title()
    return f"Do you experience {feature_readable}?"

