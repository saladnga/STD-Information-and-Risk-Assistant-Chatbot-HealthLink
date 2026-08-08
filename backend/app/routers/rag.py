"""
RAG (Retrieval-Augmented Generation) router.
Provides endpoints for uploading PDFs and asking questions with RAG.
"""
import os
import sys
import hashlib
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.ingest_pdf import ingest_pdf
from rag.retriever import retrieve_and_answer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


class QuestionRequest(BaseModel):
    question: str
    max_results: Optional[int] = 5
    temperature: Optional[float] = 0.1
    similarity_threshold: Optional[float] = 0.5  # Minimum similarity score (0.0-1.0)
    use_reranking: Optional[bool] = False  # Enable cross-encoder reranking
    rerank_top_k: Optional[int] = 10  # Number of candidates to rerank


class QuestionResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    confidence: Optional[float] = None
    num_chunks_retrieved: int


class UploadRequest(BaseModel):
    use_ocr: Optional[bool] = False  # Force OCR even if text extraction works
    ocr_fallback: Optional[bool] = True  # Use OCR if text extraction fails
    ocr_dpi: Optional[int] = 300  # DPI for OCR (higher = better quality, slower)


class UploadResponse(BaseModel):
    status: str
    message: str
    filename: str
    chunks_ingested: int
    file_size_bytes: int
    file_path: str
    extraction_method: Optional[str] = None  # "text", "ocr", or "text_with_ocr_fallback"
    text_length: Optional[int] = None


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    use_ocr: Optional[bool] = Form(False),
    ocr_fallback: Optional[bool] = Form(True),
    ocr_dpi: Optional[int] = Form(300)
):
    """
    Upload and ingest a medical PDF document for RAG.
    
    The PDF will be:
    1. Saved to data/pdf/ directory
    2. Extracted text from all pages (using text extraction or OCR)
    3. Chunked into overlapping segments
    4. Embedded using OpenAI embeddings
    5. Stored in Supabase pgvector
    
    Args:
        file: PDF file to upload
        use_ocr: If True, force OCR extraction (skip text extraction)
        ocr_fallback: If True, automatically use OCR if text extraction fails
        ocr_dpi: DPI for OCR image conversion (300-600 recommended, higher = better quality but slower)
    
    Returns information about the ingestion process.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a .pdf file."
        )
    
    # Validate file size (e.g., max 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds maximum allowed size (50MB)"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )
    
    try:
        # Create PDF directory if it doesn't exist
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pdf_dir = os.path.join(current_dir, "data", "pdf")
        os.makedirs(pdf_dir, exist_ok=True)
        
        # Generate a safe filename (handle duplicate names)
        original_filename = file.filename
        safe_filename = "".join(c for c in original_filename if c.isalnum() or c in ".-_ ")
        
        # Create unique filename if file exists
        file_path = os.path.join(pdf_dir, safe_filename)
        counter = 1
        while os.path.exists(file_path):
            name, ext = os.path.splitext(safe_filename)
            file_path = os.path.join(pdf_dir, f"{name}_{counter}{ext}")
            counter += 1
        
        # Save uploaded file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        logger.info(f"Saved PDF file: {file_path} ({file_size} bytes)")
        
        # Validate OCR parameters
        if ocr_dpi < 100 or ocr_dpi > 1200:
            raise HTTPException(
                status_code=400,
                detail="ocr_dpi must be between 100 and 1200"
            )
        
        # Ingest the PDF into vector database
        logger.info(f"Ingesting PDF: {file_path} (use_ocr={use_ocr}, ocr_fallback={ocr_fallback}, ocr_dpi={ocr_dpi})")
        result = ingest_pdf(
            pdf_path=file_path,
            use_ocr=use_ocr,
            ocr_fallback=ocr_fallback,
            ocr_dpi=ocr_dpi
        )
        
        chunks_ingested = result.get("chunks", 0)
        extraction_method = result.get("extraction_method", "unknown")
        text_length = result.get("text_length", 0)
        
        logger.info(f"Successfully ingested {chunks_ingested} chunks from {original_filename} using {extraction_method}")
        
        return UploadResponse(
            status="success",
            message=f"PDF '{original_filename}' ingested successfully. {chunks_ingested} chunks added to vector database using {extraction_method}.",
            filename=original_filename,
            chunks_ingested=chunks_ingested,
            file_size_bytes=file_size,
            file_path=file_path,
            extraction_method=extraction_method,
            text_length=text_length
        )
        
    except ImportError as e:
        logger.error(f"PDF library import error: {e}")
        raise HTTPException(
            status_code=500,
            detail="PDF processing library not available. Please install PyPDF2 or pypdf: pip install PyPDF2"
        )
    except Exception as e:
        logger.error(f"Error processing PDF: {e}", exc_info=True)
        # Clean up file if ingestion failed
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question using RAG (Retrieval-Augmented Generation).
    
    This endpoint:
    1. Retrieves top-k most relevant chunks from uploaded documents
    2. Builds grounded context with proper citations
    3. Calls LLM with no-hallucination prompt
    4. Returns answer with citations and source information
    
    The answer is guaranteed to be based only on the provided context.
    If the context doesn't contain enough information, the answer will explicitly state this.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )
    
    if request.max_results < 1 or request.max_results > 20:
        raise HTTPException(
            status_code=400,
            detail="max_results must be between 1 and 20"
        )
    
    if request.temperature < 0 or request.temperature > 2:
        raise HTTPException(
            status_code=400,
            detail="temperature must be between 0 and 2"
        )
    
    if request.similarity_threshold < 0 or request.similarity_threshold > 1:
        raise HTTPException(
            status_code=400,
            detail="similarity_threshold must be between 0 and 1"
        )
    
    if request.rerank_top_k < request.max_results:
        raise HTTPException(
            status_code=400,
            detail="rerank_top_k must be >= max_results"
        )
    
    try:
        logger.info(f"Processing question: {request.question[:100]}...")
        logger.info(f"Retrieval params: max_results={request.max_results}, similarity_threshold={request.similarity_threshold}, use_reranking={request.use_reranking}")
        
        # Retrieve and generate answer
        answer, sources, confidence, citations = retrieve_and_answer(
            question=request.question,
            max_results=request.max_results,
            temperature=request.temperature,
            similarity_threshold=request.similarity_threshold,
            use_reranking=request.use_reranking,
            rerank_top_k=request.rerank_top_k
        )
        
        logger.info(f"Generated answer with {len(sources)} sources and {len(citations)} citations")
        
        return QuestionResponse(
            answer=answer,
            sources=sources,
            citations=citations,
            confidence=confidence,
            num_chunks_retrieved=len(sources)
        )
        
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing question: {str(e)}"
        )


@router.get("/stats")
async def get_rag_stats():
    """
    Get statistics about the RAG system.
    Returns information about ingested documents and chunks.
    """
    try:
        from rag.retriever import supabase
        
        rows = supabase.table("document_chunks").select("source").execute().data
        sources = sorted({row["source"] for row in rows})
        
        return {
            "total_chunks": len(rows),
            "unique_sources": len(sources),
            "sources": sources
        }
    
    except Exception as e:
        logger.error(f"Error getting RAG stat: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting RAG statistics: {str(e)}"
        )
