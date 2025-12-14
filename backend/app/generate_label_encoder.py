"""
Generate label_encoder.json from existing model.joblib or from known disease classes.
Creates mappings: class_to_index and index_to_class.
"""
import json
import os
import sys
from datetime import datetime

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def generate_label_encoder():
    """Generate label_encoder.json from model.joblib or from known classes."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "model.joblib")
    csv_path = os.path.join(os.path.dirname(current_dir), "synthetic_data.csv")
    label_encoder_path = os.path.join(current_dir, "label_encoder.json")
    
    classes = None
    
    # Try to load from model.joblib first (most accurate)
    if JOBLIB_AVAILABLE and os.path.exists(model_path):
        try:
            model, label_encoder, features = joblib.load(model_path)
            classes = label_encoder.classes_.tolist()
            print(f"✓ Loaded {len(classes)} classes from model.joblib")
        except Exception as e:
            print(f"Warning: Could not load from model.joblib: {e}")
    
    # Fallback: Load from CSV to get unique classes
    if classes is None and PANDAS_AVAILABLE and os.path.exists(csv_path):
        try:
            # Read just the ground_truth column to get unique classes
            df = pd.read_csv(csv_path, usecols=["ground_truth"])
            classes = sorted(df["ground_truth"].unique().tolist())
            print(f"✓ Loaded {len(classes)} classes from CSV")
        except Exception as e:
            print(f"Warning: Could not load from CSV: {e}")
    
    # Final fallback: Use known disease classes (alphabetically sorted as LabelEncoder does)
    if classes is None:
        classes = [
            "BV",
            "Chlamydia",
            "Gonorrhea",
            "Healthy",
            "Hepatitis B",
            "Hepatitis C",
            "Herpes",
            "HIV",
            "HPV",
            "Mycoplasma genitalium",
            "PID",
            "Pubic Lice",
            "Scabies",
            "Syphilis",
            "Trichomoniasis",
            "UTI"
        ]
        print(f"✓ Using default {len(classes)} classes")
    
    # Create mappings
    class_to_index = {cls: int(idx) for idx, cls in enumerate(classes)}
    index_to_class = {int(idx): cls for idx, cls in enumerate(classes)}
    
    label_mapping = {
        "description": "Label encoder mapping for disease classes. Maps class names to indices and vice versa.",
        "version": "1.0",
        "num_classes": len(classes),
        "classes": classes,  # Ordered list of classes
        "class_to_index": class_to_index,  # {"Healthy": 0, "Chlamydia": 1, ...}
        "index_to_class": index_to_class  # {0: "Healthy", 1: "Chlamydia", ...}
    }
    
    # Save to file
    try:
        with open(label_encoder_path, "w") as f:
            json.dump(label_mapping, f, indent=2)
        print(f"✓ Created label_encoder.json at {label_encoder_path}")
        print(f"  - Total classes: {len(classes)}")
        print(f"\nClass to Index mapping:")
        for cls, idx in sorted(class_to_index.items(), key=lambda x: x[1]):
            print(f"  {cls}: {idx}")
        return True
    except Exception as e:
        print(f"Error: Could not write label_encoder.json: {e}")
        return False


if __name__ == "__main__":
    success = generate_label_encoder()
    sys.exit(0 if success else 1)

