# Quick Start Guide

## Fix the Syntax Error (Already Fixed)

The syntax error in `model.py` has been fixed. The `global` declaration is now at the beginning of the `get_feature_columns()` function.

## Install Dependencies

### Option 1: Install all dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Option 2: Install only critical dependencies (faster)

```bash
pip install fastapi uvicorn pandas numpy xgboost scikit-learn spacy chromadb openai python-dotenv pypdf
```

### Option 3: Use the setup script

```bash
cd backend/app
python setup_and_run.py
```

## Run the Server

### Method 1: Using the run script

```bash
cd backend/app
python run_server.py
```

### Method 2: Using uvicorn directly

```bash
cd backend/app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Method 3: Using Python

```bash
cd backend/app
python main.py
```

## Verify Server is Running

1. Open browser: http://localhost:8000/
2. Check API docs: http://localhost:8000/docs
3. Test with curl:
   ```bash
   curl http://localhost:8000/
   ```

## Common Issues

### Issue: `ModuleNotFoundError: No module named 'xgboost'`

**Solution:** Install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

### Issue: `ModuleNotFoundError: No module named 'fastapi'`

**Solution:** Install FastAPI:

```bash
pip install fastapi uvicorn
```

### Issue: Model not found

**Solution:** Train the model first:

```bash
# Using the API
curl -X POST http://localhost:8000/train

# Or directly
cd backend/app
python -c "from model import train_model; train_model()"
```

### Issue: Port already in use

**Solution:** Change the port:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## Next Steps

1. **Train the model** (if not already trained):

   - POST to `/train` endpoint
   - Or run `python model.py` directly

2. **Test predictions**:

   - POST to `/predict` with symptom text
   - Use the interactive docs at `/docs`

3. **Upload PDFs for RAG**:
   - POST to `/rag/upload` with PDF file
   - Ask questions using `/rag/ask`

## Need Help?

- Check the logs in the terminal
- Visit http://localhost:8000/docs for API documentation
- Check `START_SERVER.md` for more details
