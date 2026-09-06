import json
import os

from model import process_text_to_feature

FEATURE_SPEC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "feature_spec.json"
)

with open(FEATURE_SPEC_PATH) as f:
    BASE_FEATURES = json.load(f)["features"]


def test_symptom_present_is_detected():
    features = process_text_to_feature("I have a fishy odor", BASE_FEATURES)
    assert features["odor_fishy"] == 1


def test_negated_symptom_is_not_detected():
    features = process_text_to_feature("I have no odor", BASE_FEATURES)
    assert features["odor_fishy"] == 0


def test_unrelated_features_stay_zero():
    features = process_text_to_feature("no odor", BASE_FEATURES)
    assert features["dysuria"] == 0
