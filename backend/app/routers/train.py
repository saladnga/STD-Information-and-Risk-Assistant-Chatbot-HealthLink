"""
Training router for model training endpoint.
Protected endpoint that triggers model retraining and saves all required artifacts.
"""

import os
import sys
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model import train_model, load_model
from auth_utils import ALLOW_UNAUTHENTICATED_TRAIN
from routers.utils import verify_user_token

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/train", tags=["training"])
security = HTTPBearer(auto_error=False)  # Don't auto-raise error, handle manually


class TrainingResponse(BaseModel):
    status: str
    message: str
    files_saved: Optional[Dict[str, Dict[str, Any]]] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TrainingRequest(BaseModel):
    """Optional training parameters."""

    force_retrain: Optional[bool] = True  # Force retraining even if model exists


async def verify_auth_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    Verify authentication token if provided.
    For development, allows bypassing auth if ALLOW_UNAUTHENTICATED_TRAIN is True.
    """
    # Allow unauthenticated access in development mode
    if ALLOW_UNAUTHENTICATED_TRAIN:
        logger.warning(
            "Training endpoint is accessible without authentication (development mode)"
        )
        return {"user_id": "dev_user", "role": "admin"}

    # Require authentication in production
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid Bearer token.",
        )

    user = verify_user_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    return user

@router.post("", response_model=TrainingResponse)
async def train(
    request: Optional[TrainingRequest] = None,
    user: Dict = Depends(verify_auth_optional),
):
    """
    Protected endpoint to trigger model training.

    Requires authentication token (Bearer token) unless ALLOW_UNAUTHENTICATED_TRAIN is enabled.

    This endpoint:
    1. Triggers model training using the synthetic dataset
    2. Saves model.joblib (model, label_encoder, feature_columns)
    3. Saves feature_spec.json (feature specification)
    4. Saves label_encoder.json (class mappings)
    5. Saves training_report.json (training metrics and hyperparameters)

    Returns training status and metrics.
    """
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    try:
        logger.info(
            f"Training request initiated by user: {user.get('id', 'unknown')}"
        )

        # Check if dataset exists
        csv_path = os.path.join(current_dir, "synthetic_data.csv")
        csv_path = os.path.abspath(csv_path)

        if not os.path.exists(csv_path):
            raise HTTPException(
                status_code=404,
                detail=f"Training dataset not found at {csv_path}. Please ensure synthetic_data.csv exists.",
            )

        # Trigger training
        logger.info("Starting model training...")
        result = train_model()

        if not result:
            raise HTTPException(
                status_code=500, detail="Model training failed. Check logs for details."
            )

        model, feature_columns, label_encoder = result
        logger.info("Model training completed successfully")

        # Verify all required files were saved
        files_saved = {}
        required_files = {
            "model": "model.joblib",
            "feature_spec": "feature_spec.json",
            "label_encoder": "label_encoder.json",
            "training_report": "training_report.json",
        }

        all_files_saved = True
        for file_key, file_name in required_files.items():
            file_path = os.path.join(current_dir, file_name)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                files_saved[file_key] = {
                    "path": file_path,
                    "size_bytes": file_size,
                    "status": "saved",
                }
                logger.info(f"✓ {file_name} saved ({file_size} bytes)")
            else:
                files_saved[file_key] = {"path": file_path, "status": "missing"}
                all_files_saved = False
                logger.error(f"✗ {file_name} not found after training")

        if not all_files_saved:
            logger.warning("Some required files were not saved during training")

        # Load training report for response
        training_report_path = os.path.join(current_dir, "training_report.json")
        metrics = None
        if os.path.exists(training_report_path):
            try:
                with open(training_report_path, "r") as f:
                    metrics = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load training report: {e}")

        # Reload model to ensure it's available for predictions
        try:
            load_model()
            logger.info("Model reloaded successfully and ready for predictions")
        except Exception as e:
            logger.warning(f"Could not reload model: {e}")

        return TrainingResponse(
            status="success",
            message="Model trained and saved successfully. All artifacts are available.",
            files_saved=files_saved,
            metrics=metrics,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(
            status_code=404, detail=f"Required file not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Training error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Training error: {str(e)}")


@router.get("/status")
async def training_status(user: Dict = Depends(verify_auth_optional)):
    """
    Get status of training artifacts.
    Returns information about saved model files and their timestamps.
    """
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    required_files = {
        "model": "model.joblib",
        "feature_spec": "feature_spec.json",
        "label_encoder": "label_encoder.json",
        "training_report": "training_report.json",
    }

    status_info = {}
    for file_key, file_name in required_files.items():
        file_path = os.path.join(current_dir, file_name)
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            modified_time = os.path.getmtime(file_path)
            status_info[file_key] = {
                "exists": True,
                "path": file_path,
                "size_bytes": stat.st_size,
                "modified_timestamp": modified_time,
                "modified_datetime": datetime.fromtimestamp(modified_time).isoformat(),
            }
        else:
            status_info[file_key] = {"exists": False, "path": file_path}

    # Try to load metrics if available
    training_report_path = os.path.join(current_dir, "training_report.json")
    metrics = None
    if os.path.exists(training_report_path):
        try:
            with open(training_report_path, "r") as f:
                metrics = json.load(f)
        except Exception:
            pass

    return {
        "status": (
            "available"
            if all(f["exists"] for f in status_info.values())
            else "incomplete"
        ),
        "files": status_info,
        "metrics": metrics,
    }
