import json
import pandas as pd
import os
import numpy as np
import re
from typing import List, Optional, Tuple

from xgboost.sklearn import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, log_loss, top_k_accuracy_score, accuracy_score
from sklearn.calibration import calibration_curve
from sklearn.preprocessing import LabelEncoder
import joblib


# Load resources and configuration
current_dir = os.path.dirname(os.path.abspath(__file__))

# Load a dictionary that maps detected symptom phrases to model feature names
with open(os.path.join(current_dir, "symptom_map.json"), "r") as x:
    symptom_map = json.load(x)

# Store column order used in training (for inference)
model_feature_column = []

# Global model and encoder (loaded at runtime)
_model = None
_label_encoder = None


def process_text_to_feature(text: str, base_feature: list) -> dict:
    """
    Convert text description to feature dictionary using simple regex/substring matching.
    No spaCy dependency - uses symptom_map.json for pattern matching.
    
    Args:
        text: Text description of symptoms
        base_feature: List of feature column names in exact training order
    
    Returns:
        Dictionary with all features from base_feature, values set to 0 or 1
    """
    # 1. Initialize all features to 0 (ensures all features are present)
    features = {col: 0 for col in base_feature}

    # 2. Normalize text for matching (lowercase, remove extra whitespace)
    text_lower = text.lower().strip()
    text_normalized = re.sub(r'\s+', ' ', text_lower)  # Normalize whitespace

    # 3. Match symptom phrases from symptom_map using substring matching
    # Sort by length (longest first) to match more specific phrases first
    symptom_phrases = sorted(symptom_map.keys(), key=len, reverse=True)
    
    for phrase in symptom_phrases:
        phrase_lower = phrase.lower().strip()
        # Check if phrase appears in text (word boundary matching for better accuracy)
        # Use word boundary regex for whole-word matching when possible
        if len(phrase_lower.split()) == 1:
            # Single word - use word boundary
            pattern = r'\b' + re.escape(phrase_lower) + r'\b'
            if re.search(pattern, text_normalized, re.IGNORECASE):
                feature_name = symptom_map[phrase]
                if feature_name and feature_name in features:
                    features[feature_name] = 1
        else:
            # Multi-word phrase - use simple substring match
            if phrase_lower in text_normalized:
                feature_name = symptom_map[phrase]
                if feature_name and feature_name in features:
                    features[feature_name] = 1

    # Add default demographic / behavioral attributes (if they exist in base_feature)
    if "age" in features:
        features["age"] = 30
    if "new_partners_last_3_months" in features:
        features["new_partners_last_3_months"] = 1
    if "condom_use_consistency_never" in features:
        features["condom_use_consistency_never"] = 0
    if "condom_use_consistency_sometimes" in features:
        features["condom_use_consistency_sometimes"] = 1

    # Ensure all base_feature columns are present (defensive check)
    for col in base_feature:
        if col not in features:
            features[col] = 0

    return features


def compute_symptom_probabilities(df: pd.DataFrame, label_encoder: LabelEncoder) -> dict:
    """
    Compute P(symptom=1|disease) from training data.
    
    Returns:
        Dictionary mapping disease -> symptom -> probability
    """
    symptom_probs = {}
    
    # Get disease classes
    diseases = label_encoder.classes_
    
    # Get symptom features (exclude non-symptom features)
    non_symptom_features = {"age", "new_partners_last_3_months", "condom_use_consistency_never", "condom_use_consistency_sometimes"}
    symptom_features = [f for f in df.columns if f != "ground_truth" and f not in non_symptom_features]
    
    # For each disease, compute P(symptom=1|disease)
    for disease in diseases:
        disease_data = df[df["ground_truth"] == disease]
        
        if len(disease_data) == 0:
            symptom_probs[disease] = {}
            continue
        
        disease_probs = {}
        for symptom in symptom_features:
            # P(symptom=1|disease) = count(symptom=1 and disease) / count(disease)
            prob = disease_data[symptom].mean()
            disease_probs[symptom] = float(prob)
        
        symptom_probs[disease] = disease_probs
    
    return symptom_probs


# Load the synthetic dataset, trains an XGBoost multi-class classifier, and saves the trained model + encoder for later inference
def train_model():
    global model_feature_column
    print("Loading data.....")

    # 1. Load dataset
    try:
        # csv_path = os.path.join(
        #     os.path.dirname(current_dir), "..", "synthetic_data.csv"
        # )
        # csv_path = os.path.abspath(csv_path)
        # df = pd.read_csv(csv_path)
        csv_path = os.path.join(current_dir, "synthetic_data.csv")
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: data not found at {csv_path}")
        return

    # 2. Split features and label
    y = df["ground_truth"]
    x = df.drop("ground_truth", axis=1)

    # 3. Encode labels numerically for XGBoost
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    # 4. Preserve feature column order
    model_feature_column = x.columns.tolist()

    # 5. Train-test split with stratification for class balance
    X_train, X_test, y_train, y_test = train_test_split(
        x, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    print("Using XGBoost model...")

    # 6. Define XGBoost parameters optimized for better accuracy
    model = xgb.XGBClassifier(
        objective="multi:softprob",  # Use softprob for probabilities
        num_class=len(label_encoder.classes_),
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        max_depth=8,  # Increased depth for more complex patterns
        learning_rate=0.025,  # Lower learning rate for better convergence
        n_estimators=1200,  # More estimators (early stopping will prevent overfitting)
        min_child_weight=1,  # Slightly lower for more flexibility
        subsample=0.95,  # Slightly higher for more data usage
        colsample_bytree=0.9,  # Slightly higher for more feature usage
        gamma=0.05,  # Minimum loss reduction for split
        reg_alpha=0.1,  # L1 regularization
        reg_lambda=1.2,
        max_delta_step=2,  # L2 regularization
        scale_pos_weight=1  # Handled by sample_weight instead
    )

    # 7. Compute class weights only for training data (after split)
    train_class_weights = compute_class_weight(
        "balanced", classes=np.unique(y_train), y=y_train
    )
    weight_dict = dict(zip(np.unique(y_train), train_class_weights))
    
    # 🎯 Boost thêm trọng số cho nhóm khó học (HPV, Mycoplasma, Healthy)
    for cls_name, boost in {"HPV": 1.5, "Mycoplasma genitalium": 1.7, "Healthy": 1.3}.items():
        if cls_name in label_encoder.classes_:
            idx = list(label_encoder.classes_).index(cls_name)
            weight_dict[idx] *= boost

    # 8. Create sample weights for training set only
    sample_weight_train = np.array([weight_dict[label] for label in y_train])
    print(type(model))
    # 9. Fit the model with early stopping for better generalization
    model.fit(
        X_train, 
        y_train, 
        sample_weight=sample_weight_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        early_stopping_rounds=40,
        verbose=50
    )

    # 10. Evaluate model performance on test data
    print("Model evaluation")
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)
    
    # Classification report
    report = classification_report(y_test, y_pred, target_names=label_encoder.classes_, output_dict=True)
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))
    
    # Compute additional metrics
    # Logloss (multi-class logarithmic loss)
    logloss = log_loss(y_test, y_pred_proba, labels=np.arange(len(label_encoder.classes_)))
    
    # Top-1 and Top-2 accuracy
    top1_accuracy = accuracy_score(y_test, y_pred)
    top2_accuracy = top_k_accuracy_score(y_test, y_pred_proba, k=2, labels=np.arange(len(label_encoder.classes_)))
    
    # Class counts in training and test sets
    train_class_counts = {label_encoder.classes_[i]: int(count) for i, count in enumerate(np.bincount(y_train))}
    test_class_counts = {label_encoder.classes_[i]: int(count) for i, count in enumerate(np.bincount(y_test))}
    
    # Calibration score (Brier score for multi-class)
    # For multi-class, we compute calibration for each class and average
    calibration_scores = []
    for class_idx in range(len(label_encoder.classes_)):
        # Binary calibration for each class (one-vs-rest)
        y_true_binary = (y_test == class_idx).astype(int)
        y_prob_binary = y_pred_proba[:, class_idx]
        
        if len(np.unique(y_true_binary)) > 1:  # Only if both classes are present
            try:
                fraction_of_positives, mean_predicted_value = calibration_curve(
                    y_true_binary, y_prob_binary, n_bins=10, strategy='uniform'
                )
                # Brier score for this class
                brier_score = np.mean((y_prob_binary - y_true_binary) ** 2)
                calibration_scores.append({
                    "class": label_encoder.classes_[class_idx],
                    "brier_score": float(brier_score),
                    "calibration_curve": {
                        "fraction_of_positives": [float(x) for x in fraction_of_positives],
                        "mean_predicted_value": [float(x) for x in mean_predicted_value]
                    }
                })
            except Exception as e:
                # Skip if calibration curve computation fails
                pass
    
    # Average Brier score (lower is better, 0 is perfect calibration)
    avg_brier_score = np.mean([s["brier_score"] for s in calibration_scores]) if calibration_scores else None
    
    # Get best iteration from early stopping
    best_iteration = model.get_booster().best_iteration if hasattr(model, 'get_booster') else None
    if best_iteration is None:
        best_iteration = model.best_iteration if hasattr(model, 'best_iteration') else None

    # 11. Save model, label encoder, and feature columns
    model_filename = os.path.join(current_dir, "model.joblib")
    joblib.dump((model, label_encoder, model_feature_column), model_filename)
    print(f"Successfully trained and saved model to {model_filename}")

    # 12. Save feature specification JSON with exact order and metadata
    feature_spec_path = os.path.join(current_dir, "feature_spec.json")
    feature_spec = {
        "description": "Exact ordered list of feature columns used during training. Order must match 1:1 during inference.",
        "version": "1.0",
        "num_features": len(model_feature_column),
        "features": model_feature_column,  # Exact order as used in training
        "feature_types": {
            "symptom_features": [f for f in model_feature_column if f not in {
                "age", "new_partners_last_3_months", 
                "condom_use_consistency_never", "condom_use_consistency_sometimes"
            }],
            "demographic_features": ["age"],
            "behavioral_features": [
                "new_partners_last_3_months",
                "condom_use_consistency_never",
                "condom_use_consistency_sometimes"
            ]
        },
        "timestamp": pd.Timestamp.now().isoformat()
    }
    with open(feature_spec_path, "w") as f:
        json.dump(feature_spec, f, indent=2)
    print(f"Saved feature specification to {feature_spec_path} with {len(model_feature_column)} features in exact order")

    # 13. Save label encoder mapping JSON
    label_encoder_path = os.path.join(current_dir, "label_encoder.json")
    label_mapping = {
        "classes": label_encoder.classes_.tolist(),
        "class_to_index": {cls: int(idx) for idx, cls in enumerate(label_encoder.classes_)},
        "index_to_class": {int(idx): cls for idx, cls in enumerate(label_encoder.classes_)}
    }
    with open(label_encoder_path, "w") as f:
        json.dump(label_mapping, f, indent=2)
    print(f"Saved label encoder to {label_encoder_path}")

    # 14. Compute and save symptom probabilities P(symptom=1|disease) from training data
    symptom_probs_path = os.path.join(current_dir, "symptom_probabilities.json")
    symptom_probs = compute_symptom_probabilities(df, label_encoder)
    with open(symptom_probs_path, "w") as f:
        json.dump({
            "description": "Conditional probabilities P(symptom=1|disease) computed from training data",
            "probabilities": symptom_probs
        }, f, indent=2)
    print(f"Saved symptom probabilities to {symptom_probs_path}")

    # 15. Save training report with comprehensive metrics
    training_report_path = os.path.join(current_dir, "training_report.json")
    training_report = {
        "description": "Comprehensive training report with metrics, class counts, calibration scores, and hyperparameters",
        "timestamp": pd.Timestamp.now().isoformat(),
        "model_type": "XGBoost",
        "num_classes": len(label_encoder.classes_),
        "num_features": len(model_feature_column),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "metrics": {
            "logloss": float(logloss),
            "top1_accuracy": float(top1_accuracy),
            "top2_accuracy": float(top2_accuracy),
            "accuracy": float(report.get("accuracy", top1_accuracy)),
            "macro_avg": {
                "precision": float(report.get("macro avg", {}).get("precision", 0.0)),
                "recall": float(report.get("macro avg", {}).get("recall", 0.0)),
                "f1_score": float(report.get("macro avg", {}).get("f1-score", 0.0)),
                "support": int(report.get("macro avg", {}).get("support", 0))
            },
            "weighted_avg": {
                "precision": float(report.get("weighted avg", {}).get("precision", 0.0)),
                "recall": float(report.get("weighted avg", {}).get("recall", 0.0)),
                "f1_score": float(report.get("weighted avg", {}).get("f1-score", 0.0)),
                "support": int(report.get("weighted avg", {}).get("support", 0))
            }
        },
        "calibration": {
            "avg_brier_score": float(avg_brier_score) if avg_brier_score is not None else None,
            "per_class_calibration": calibration_scores,
            "note": "Brier score: lower is better (0 = perfect calibration). Calibration curve shows predicted probability vs actual frequency."
        },
        "class_counts": {
            "train": train_class_counts,
            "test": test_class_counts,
            "train_total": int(len(X_train)),
            "test_total": int(len(X_test))
        },
        "classification_report": report,
        "hyperparameters": {
            "objective": "multi:softprob",
            "num_class": len(label_encoder.classes_),
            "eval_metric": "mlogloss",
            "random_state": 42,
            "max_depth": 6,
            "learning_rate": 0.05,
            "n_estimators": 500,
            "min_child_weight": 2,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "gamma": 0.1,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "early_stopping_rounds": 20,
            "best_iteration": int(best_iteration) if best_iteration is not None else None
        },
        "training_config": {
            "test_size": 0.2,
            "stratify": True,
            "class_weights": "balanced",
            "sample_weights": True,
            "early_stopping": True
        }
    }
    with open(training_report_path, "w") as f:
        json.dump(training_report, f, indent=2, default=str)
    print(f"Saved training report to {training_report_path}")
    print(f"  - Logloss: {logloss:.4f}")
    print(f"  - Top-1 Accuracy: {top1_accuracy:.4f}")
    print(f"  - Top-2 Accuracy: {top2_accuracy:.4f}")
    print(f"  - Avg Brier Score (calibration): {avg_brier_score:.4f}" if avg_brier_score else "  - Calibration: N/A")

    return model, model_feature_column, label_encoder


def load_feature_spec() -> Optional[List[str]]:
    """
    Load feature specification from feature_spec.json.
    Returns the exact ordered list of feature columns used during training.
    
    Returns:
        List of feature column names in exact training order, or None if not found
    """
    feature_spec_path = os.path.join(current_dir, "feature_spec.json")
    try:
        if os.path.exists(feature_spec_path):
            with open(feature_spec_path, "r") as f:
                feature_spec = json.load(f)
                features = feature_spec.get("features", [])
                if features:
                    print(f"Loaded feature spec with {len(features)} features from {feature_spec_path}")
                    return features
    except Exception as e:
        print(f"Warning: Could not load feature spec: {e}")
    return None


def validate_feature_order(features: List[str], expected_order: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that feature order matches expected order exactly.
    
    Args:
        features: Current feature list
        expected_order: Expected feature order from training
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check if lengths match
    if len(features) != len(expected_order):
        errors.append(f"Feature count mismatch: got {len(features)}, expected {len(expected_order)}")
    
    # Check if all expected features are present
    missing_features = set(expected_order) - set(features)
    if missing_features:
        errors.append(f"Missing features: {missing_features}")
    
    # Check for extra features
    extra_features = set(features) - set(expected_order)
    if extra_features:
        errors.append(f"Extra features: {extra_features}")
    
    # Check exact order
    if features != expected_order:
        # Find first mismatch
        for i, (feat, expected) in enumerate(zip(features, expected_order)):
            if feat != expected:
                errors.append(f"Feature order mismatch at index {i}: got '{feat}', expected '{expected}'")
                break
    
    return len(errors) == 0, errors


def load_model():
    """Load model, label encoder, and feature columns from disk."""
    global _model, _label_encoder, model_feature_column
    if _model is None:
        model_path = os.path.join(current_dir, "model.joblib")
        try:
            _model, _label_encoder, model_feature_column = joblib.load(model_path)
            print(f"Model loaded successfully with {len(model_feature_column)} features")
            
            # Validate feature order against feature_spec.json if available
            feature_spec_features = load_feature_spec()
            if feature_spec_features:
                is_valid, errors = validate_feature_order(model_feature_column, feature_spec_features)
                if not is_valid:
                    print(f"WARNING: Feature order mismatch between model.joblib and feature_spec.json:")
                    for error in errors:
                        print(f"  - {error}")
                    print("Using feature order from model.joblib")
                else:
                    print("Feature order validated against feature_spec.json: OK")
        except (FileNotFoundError, ValueError) as e:
            print(f"Warning: Could not load model: {e}")
            # Try to load feature spec as fallback
            model_feature_column = load_feature_spec() or []
            if model_feature_column:
                print(f"Loaded feature spec as fallback with {len(model_feature_column)} features")
    return _model, _label_encoder, model_feature_column


def get_model():
    """Get the loaded model."""
    if _model is None:
        load_model()
    return _model


def get_label_encoder():
    """Get the loaded label encoder."""
    if _label_encoder is None:
        load_model()
    return _label_encoder


def get_feature_columns() -> List[str]:
    """
    Get the feature column list in exact training order.
    Ensures features are in the same order as during training for 1:1 inference matching.
    
    Returns:
        List of feature column names in exact training order
    """
    global model_feature_column
    
    if not model_feature_column:
        load_model()
    
    # If still empty, try loading from feature_spec.json
    if not model_feature_column:
        model_feature_column_fallback = load_feature_spec()
        if model_feature_column_fallback:
            model_feature_column = model_feature_column_fallback
    
    return model_feature_column


def get_nlp():
    """Get the NLP pipeline."""
    global _nlp
    if _nlp is None:
        _nlp = initialize_nlp()
    return _nlp


if __name__ == "__main__":
    result = train_model()

    if result:
        model, feature_column, label_encoder = result
        print("Testing....")

        # Testing input
        text = "it burns when i pee and i have a bad odor"

        # Convert inputs to feature vector
        feature_dict = process_text_to_feature(text, feature_column)
        # Ensure features are in the correct order matching training data
        feature_df = pd.DataFrame([feature_dict], columns=feature_column)
        # Verify all features are present (fill missing with 0)
        missing_cols = set(feature_column) - set(feature_df.columns)
        if missing_cols:
            for col in missing_cols:
                feature_df[col] = 0
            feature_df = feature_df[feature_column]  # Reorder columns

        # Predict probabilities and most likely case
        prediction_probability = model.predict_proba(feature_df)
        prediction_class = model.predict(feature_df)
        prediction_class_name = label_encoder.inverse_transform(prediction_class)[0]

        # Map each class to its probability
        class_probability = dict(zip(label_encoder.classes_, prediction_probability[0]))

        # Display result
        print(f"Input text: '{text}'")
        print(
            f"Mapped features: dysuria={feature_dict.get('dysuria', 0)}, odor_fishy={feature_dict.get('odor_fishy', 0)}"
        )
        print(f"Predicted Class: {prediction_class_name}")
        print(f"Prediction Probability: {class_probability}")