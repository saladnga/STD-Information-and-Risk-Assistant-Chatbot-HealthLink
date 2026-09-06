"""
Generate feature_spec.json from existing model.joblib or CSV file.
This script creates the feature specification file with exact feature order.
"""
import json
import os
import sys
from datetime import datetime
import joblib
import pandas as pd


def generate_feature_spec():
    """Generate feature_spec.json from model.joblib or CSV."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "model.joblib")
    csv_path = os.path.join(os.path.dirname(current_dir), "synthetic_data.csv")
    feature_spec_path = os.path.join(current_dir, "feature_spec.json")
    
    features = None
    
    # Try to load from model.joblib first (most accurate)
    if os.path.exists(model_path):
        try:
            model, label_encoder, features = joblib.load(model_path)
            print(f"✓ Loaded {len(features)} features from model.joblib")
        except Exception as e:
            print(f"Warning: Could not load from model.joblib: {e}")
    
    # Fallback to CSV if model.joblib not available
    if features is None and os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, nrows=1)  # Just read header
            features = [col for col in df.columns if col != "ground_truth"]
            print(f"✓ Loaded {len(features)} features from CSV")
        except Exception as e:
            print(f"Error: Could not load from CSV: {e}")
            return False
    
    if features is None:
        print("Error: Could not load features from model.joblib or CSV")
        return False
    
    # Categorize features
    non_symptom_features = {
        "age", "new_partners_last_3_months",
        "condom_use_consistency_never", "condom_use_consistency_sometimes"
    }
    
    symptom_features = [f for f in features if f not in non_symptom_features]
    demographic_features = ["age"] if "age" in features else []
    behavioral_features = [
        f for f in features
        if f in ["new_partners_last_3_months", "condom_use_consistency_never", "condom_use_consistency_sometimes"]
    ]
    
    # Create feature specification
    feature_spec = {
        "description": "Exact ordered list of feature columns used during training. Order must match 1:1 during inference.",
        "version": "1.0",
        "num_features": len(features),
        "features": features,  # Exact order
        "feature_types": {
            "symptom_features": symptom_features,
            "demographic_features": demographic_features,
            "behavioral_features": behavioral_features
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Save to file
    try:
        with open(feature_spec_path, "w") as f:
            json.dump(feature_spec, f, indent=2)
        print(f"- Created feature_spec.json at {feature_spec_path}")
        print(f"- Total features: {len(features)}")
        print(f"- Symptom features: {len(symptom_features)}")
        print(f"- Demographic features: {len(demographic_features)}")
        print(f"- Behavioral features: {len(behavioral_features)}")
        print(f"\nFirst 5 features: {features[:5]}")
        print(f"Last 5 features: {features[-5:]}")
        return True
    except Exception as e:
        print(f"Error: Could not write feature_spec.json: {e}")
        return False


if __name__ == "__main__":
    success = generate_feature_spec()
    sys.exit(0 if success else 1)

