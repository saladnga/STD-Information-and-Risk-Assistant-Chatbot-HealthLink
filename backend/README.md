# Troy HealthLink Backend

Backend API for STD symptom prediction and health assistance using ML and RAG.

## Project Structure

```
backend/app/
├── routers/
│   ├── __init__.py
│   ├── predict.py          # /predict, /followup endpoints
│   ├── train.py            # /train endpoint (protected)
│   └── rag.py              # /rag/upload, /rag/ask endpoints
│
├── rag/
│   ├── __init__.py
│   ├── ingest_pdf.py       # PDF parsing, chunking, embedding
│   ├── retriever.py        # Document retrieval and answer generation
│   └── templates.py        # RAG prompt templates
│
├── data/
│   ├── pdf/                # Upload medical PDFs here
│   └── chroma/             # ChromaDB persistence (auto-created)
│
├── model.py                # Training + inference utilities
├── main.py                 # FastAPI app bootstrap
├── knowledge_base.py       # STD_KNOWLEDGE dictionary
├── auth_utils.py           # Authentication utilities
├── generate_data.py        # Synthetic data generation
├── supabase_client.py      # Supabase client
│
├── model.joblib            # Trained model (artifact)
├── feature_spec.json       # Feature specification
├── label_encoder.json      # Class mappings
├── training_report.json    # Training metrics
├── symptom_map.json        # Symptom text → feature mapping
├── symptom_target_rules.json  # NLP symptom detection rules
├── question_bank.json      # Follow-up questions per disease-pair
└── synthetic_data.csv      # Training dataset
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Create a `.env` file with:
   ```
   OPENAI_API_KEY=your_openai_api_key
   JWT_SECRET=your_jwt_secret
   ```

3. **Train the model:**
   ```bash
   python model.py
   ```
   This will:
   - Load `synthetic_data.csv`
   - Train XGBoost model
   - Save `model.joblib`, `feature_spec.json`, `label_encoder.json`, `training_report.json`

4. **Run the server:**
   ```bash
   python main.py
   ```
   Or using uvicorn:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### Prediction Endpoints

- **POST /predict**
  - Accepts symptom text
  - Returns prediction, probabilities, and detected symptoms
  ```json
  {
    "text": "it burns when i pee and i have a bad odor"
  }
  ```

- **POST /predict/followup**
  - Processes follow-up symptom information
  - Updates probabilities based on new information
  ```json
  {
    "text": "the discharge is thin and yellow",
    "previous_prediction": "Chlamydia",
    "previous_probabilities": {"Chlamydia": 0.7, "Gonorrhea": 0.2, ...}
  }
  ```

### Training Endpoint

- **POST /train** (Protected)
  - Triggers model retraining
  - Requires authentication token
  - Returns training status and metrics

### RAG Endpoints

- **POST /rag/upload**
  - Upload medical PDF documents
  - PDFs are parsed, chunked, embedded, and stored

- **POST /rag/ask**
  - Ask questions using RAG
  - Retrieves relevant context from uploaded documents
  ```json
  {
    "question": "What are the treatment options for chlamydia?",
    "max_results": 5
  }
  ```

## Model Training

The model uses XGBoost with optimized hyperparameters:

- **Objective**: multi:softprob
- **Max Depth**: 6
- **Learning Rate**: 0.05
- **N Estimators**: 500 (with early stopping)
- **Regularization**: L1 (0.1) + L2 (1.0)
- **Class Weights**: Balanced (handles class imbalance)

Training saves:
- `model.joblib`: Trained model, label encoder, feature columns
- `feature_spec.json`: Ordered feature list
- `label_encoder.json`: Class ↔ index mappings
- `training_report.json`: Training metrics and hyperparameters

## RAG (Retrieval-Augmented Generation)

The RAG system allows you to:

1. **Upload PDFs**: Medical documents are processed and stored in ChromaDB
2. **Ask Questions**: Questions are answered using retrieved context from uploaded documents
3. **No Hallucination**: Strict prompt templates ensure answers only use provided context

### RAG Workflow

1. Upload PDF → `rag/ingest_pdf.py`
   - Extract text
   - Chunk text (1000 chars, 200 overlap)
   - Create embeddings (OpenAI ada-002)
   - Store in ChromaDB

2. Ask Question → `rag/retriever.py`
   - Create query embedding
   - Retrieve relevant chunks
   - Generate answer with context
   - Return answer + sources

## Development

### Adding New Symptoms

1. Update `symptom_target_rules.json` with new symptom detection rules
2. Update `symptom_map.json` with symptom → feature mapping
3. Retrain the model

### Adding New Diseases

1. Update `knowledge_base.py` with disease information
2. Update `question_bank.json` with follow-up questions
3. Regenerate training data if needed
4. Retrain the model

## Requirements

See `requirements.txt` for full list. Key dependencies:

- `fastapi`: Web framework
- `xgboost`: ML model
- `scikit-learn`: ML utilities
- `spacy`, `medspacy`: NLP
- `chromadb`: Vector database
- `openai`: Embeddings and LLM
- `pypdf` or `PyPDF2`: PDF processing

## Notes

- Model must be trained before using prediction endpoints
- RAG requires uploaded PDFs before asking questions
- Authentication required for `/train` endpoint
- ChromaDB data persists in `data/chroma/`

