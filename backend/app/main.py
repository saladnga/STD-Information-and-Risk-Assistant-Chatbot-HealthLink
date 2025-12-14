"""
FastAPI application bootstrap.
Main entry point that includes all routers.
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import routers
from routers import predict, train, rag, auth, chatbot
from model import load_model


# Initialize model and NLP on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup: Load model and initialize NLP
    print("=" * 60)
    print("Initializing Troy HealthLink API")
    print("=" * 60)
    print("Loading model...")
    try:
        model, label_encoder, feature_columns = load_model()
        # Store in app state for WebSocket access
        app.state.model = model
        app.state.nlp = None  # No NLP dependencies for now
        app.state.label_encoder = label_encoder
        app.state.feature_columns = feature_columns
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"⚠ Warning: Could not load model: {e}")
        print("  Some endpoints may not work until model is trained.")
        print("  Train the model using: POST /train")
        # Set None values to prevent AttributeError
        app.state.model = None
        app.state.nlp = None
        app.state.label_encoder = None
        app.state.feature_columns = []

    print("✓ Symptom extraction ready (regex-based, no NLP dependencies)")
    print("=" * 60)
    print("Server is ready!")
    print("=" * 60)
    print()

    yield  # Application runs here

    # Shutdown: Cleanup if needed
    print("\nShutting down...")


# Create FastAPI app
app = FastAPI(
    title="Troy HealthLink API",
    description="API for STD health assistant with ML prediction and RAG capabilities",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(train.router)
app.include_router(rag.router)
app.include_router(chatbot.router)


# Root endpoint
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Troy HealthLink API is running!",
        "version": "1.0.0",
        "endpoints": {
            "predict": "/predict",
            "followup": "/predict/followup",
            "train": "/train (protected)",
            "train_status": "/train/status (protected)",
            "rag_upload": "/rag/upload",
            "rag_ask": "/rag/ask",
            "rag_stats": "/rag/stats",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
