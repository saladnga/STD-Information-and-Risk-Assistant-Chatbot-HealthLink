"""
Feature validation utilities to ensure inference features match training features exactly.
Validates feature order, presence, and types for 1:1 matching with training data.
"""
import json
import os
from typing import List, Dict, Tuple, Optional
import pandas as pd


def load_feature_spec(spec_path: Optional[str] = None) -> Optional[Dict]:
    """
    Load feature specification from feature_spec.json.
    
    Args:
        spec_path: Path to feature_spec.json (default: current_dir/feature_spec.json)
    
    Returns:
        Feature specification dictionary or None if not found
    """
    if spec_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        spec_path = os.path.join(current_dir, "feature_spec.json")
    
    try:
        if os.path.exists(spec_path):
            with open(spec_path, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading feature spec: {e}")
    return None


def get_feature_order(spec_path: Optional[str] = None) -> Optional[List[str]]:
    """
    Get the exact ordered list of features from feature_spec.json.
    
    Args:
        spec_path: Path to feature_spec.json
    
    Returns:
        List of feature names in exact training order, or None if not found
    """
    feature_spec = load_feature_spec(spec_path)
    if feature_spec:
        return feature_spec.get("features", [])
    return None


def validate_feature_dict(
    features: Dict[str, any],
    expected_order: List[str],
    allow_extra: bool = False
) -> Tuple[bool, List[str]]:
    """
    Validate a feature dictionary against expected feature order.
    
    Args:
        features: Feature dictionary to validate
        expected_order: Expected ordered list of feature names
        allow_extra: Whether to allow extra features not in expected_order
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check for missing features
    missing_features = set(expected_order) - set(features.keys())
    if missing_features:
        errors.append(f"Missing features: {sorted(missing_features)}")
    
    # Check for extra features
    if not allow_extra:
        extra_features = set(features.keys()) - set(expected_order)
        if extra_features:
            errors.append(f"Extra features not in training spec: {sorted(extra_features)}")
    
    # Check feature types (should be numeric)
    for feature in expected_order:
        if feature in features:
            value = features[feature]
            if not isinstance(value, (int, float, bool)):
                errors.append(f"Feature '{feature}' has non-numeric value: {type(value).__name__}")
    
    return len(errors) == 0, errors


def validate_feature_dataframe(
    df: pd.DataFrame,
    expected_order: List[str]
) -> Tuple[bool, List[str]]:
    """
    Validate a feature DataFrame against expected feature order.
    
    Args:
        df: DataFrame with features
        expected_order: Expected ordered list of feature names
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check if DataFrame has exactly one row
    if len(df) != 1:
        errors.append(f"DataFrame must have exactly 1 row, got {len(df)}")
    
    # Check column order
    actual_columns = list(df.columns)
    if actual_columns != expected_order:
        errors.append(f"Column order mismatch. Expected {len(expected_order)} features in exact order.")
        
        # Find first mismatch
        for i, (actual, expected) in enumerate(zip(actual_columns, expected_order)):
            if actual != expected:
                errors.append(f"  First mismatch at index {i}: got '{actual}', expected '{expected}'")
                break
        
        # Check for missing columns
        missing = set(expected_order) - set(actual_columns)
        if missing:
            errors.append(f"  Missing columns: {sorted(missing)}")
        
        # Check for extra columns
        extra = set(actual_columns) - set(expected_order)
        if extra:
            errors.append(f"  Extra columns: {sorted(extra)}")
    
    # Check for NaN values
    if df.isna().any().any():
        nan_cols = df.columns[df.isna().any()].tolist()
        errors.append(f"NaN values found in columns: {nan_cols}")
    
    return len(errors) == 0, errors


def ensure_feature_order(
    features: Dict[str, any],
    expected_order: List[str]
) -> Dict[str, any]:
    """
    Ensure feature dictionary has all features in exact expected order.
    Adds missing features with value 0.
    
    Args:
        features: Feature dictionary
        expected_order: Expected ordered list of feature names
    
    Returns:
        Feature dictionary with all features in expected order (as dict maintains insertion order in Python 3.7+)
    """
    # Create ordered dictionary with all expected features
    ordered_features = {}
    for feature in expected_order:
        ordered_features[feature] = features.get(feature, 0)
    
    return ordered_features


def create_feature_dataframe(
    features: Dict[str, any],
    expected_order: List[str]
) -> pd.DataFrame:
    """
    Create a feature DataFrame with features in exact training order.
    
    Args:
        features: Feature dictionary
        expected_order: Expected ordered list of feature names
    
    Returns:
        DataFrame with exactly 1 row and features in exact training order
    """
    # Ensure all features are present and in correct order
    ordered_features = ensure_feature_order(features, expected_order)
    
    # Create DataFrame with explicit column order
    df = pd.DataFrame([ordered_features], columns=expected_order)
    
    # Validate
    is_valid, errors = validate_feature_dataframe(df, expected_order)
    if not is_valid:
        raise ValueError(f"Feature DataFrame validation failed: {errors}")
    
    return df

