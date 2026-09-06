"""
Retriever for RAG with vector retrieval, optional cross-encoder reranking, and similarity gating.
"""

import os
import sys
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
from dotenv import load_dotenv
import logging

load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.templates import (
    format_rag_prompt,
    get_system_prompt,
    is_no_answer_response,
    get_no_answer_response,
    format_citation,
)

from supabase_client import get_supabase_client

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Supabase (pgvector)
supabase = get_supabase_client()

# Configuration
DEFAULT_SIMILARITY_THRESHOLD = 0.5  # Minimum similarity score (1 - distance)
DEFAULT_USE_RERANKING = False  # Whether to use cross-encoder reranking
DEFAULT_RERANK_TOP_K = 10  # Number of candidates to rerank

# Try to import cross-encoder for reranking (optional)
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
    # Initialize cross-encoder model (loaded lazily)
    _cross_encoder_model = None
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    _cross_encoder_model = None
    logger.warning(
        "sentence-transformers not available. Cross-encoder reranking will be disabled."
    )


def get_cross_encoder_model():
    """Lazy load cross-encoder model."""
    global _cross_encoder_model
    if _cross_encoder_model is None and CROSS_ENCODER_AVAILABLE:
        try:
            # Use a medical/healthcare-focused model if available, otherwise use a general one
            # ms-marco-MiniLM-L-6-v2 is a good general-purpose reranker
            model_name = os.getenv(
                "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
            )
            _cross_encoder_model = CrossEncoder(model_name)
            logger.info(f"Loaded cross-encoder model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
            return None
    return _cross_encoder_model


def create_query_embedding(query: str) -> List[float]:
    """Create embedding for a query using OpenAI."""
    response = openai_client.embeddings.create(
        model="text-embedding-ada-002", input=query
    )
    return response.data[0].embedding


def retrieve_relevant_chunks(
    query: str,
    max_results: int = 5,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    use_reranking: bool = DEFAULT_USE_RERANKING,
    rerank_top_k: int = DEFAULT_RERANK_TOP_K,
) -> List[Dict]:
    """
    Retrieve relevant document chunks using vector similarity.
    Args:
    - query: Search query
    - max_results: Maximum number of results to return
    - similarity_threshold: Minimum similarity score (0.0-1.0) to include results
    - use_reranking: Whether to use cross-encoder reranking
    - rerank_top_k: Number of candidates to retrieve for reranking (should be >= max_results)
    Returns:
    - List of chunks sorted by relevance (re-ranked if enabled)
    """
    
    # Step 1: Vector retrieval
    retrieve_count = rerank_top_k if use_reranking else max_results
    retrieve_count = max(retrieve_count, max_results)
    query_embedding = create_query_embedding(query)

    response = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_count": retrieve_count,
            "similarity_threshold": similarity_threshold,
        },
    ).execute()

    # Step 2: Reshape rows into the chunk format the rest of this file expects
    chunks = []
    for i, row in enumerate(response.data):
        similarity_score = row["similarity"]
        chunks.append(
            {
                "text": row["content"],
                "distance": 1.0 - similarity_score,
                "similarity_score": similarity_score,
                "relevance_score": similarity_score,
                "chunk_id": row["id"],
                "source": row.get("source", "Unknown"),
                "chunk_index": row.get("chunk_index", i),
                "total_chunks": row.get("total_chunks", 0),
                "initial_rank": i + 1,
            }
        )

    logger.info(
        f"Retrieved {len(chunks)} chunks after similarity gating (threshold={similarity_threshold})"
    )

    # Step 3: Optional cross-encoder reranking
    if use_reranking and len(chunks) > 1:
        chunks = rerank_chunks(query, chunks, top_k=max_results)
        logger.info(f"Reranked chunks using cross-encoder")
    else:
        # If not reranking, just take top max_results
        chunks = chunks[:max_results]

    return chunks


def rerank_chunks(
    query: str, 
    chunks: List[Dict], 
    top_k: int = 5
) -> List[Dict]:
    """
    Re-rank chunks using cross-encoder for better relevance.
    Args:
    - query: Search query
    - chunks: List of chunk dictionaries
    - top_k: Number of top chunks to return after reranking
    Returns:
    - Re-ranked list of chunks
    """
    if not CROSS_ENCODER_AVAILABLE:
        logger.warning("Cross-encoder not available, skipping reranking")
        return chunks[:top_k]

    cross_encoder = get_cross_encoder_model()
    if cross_encoder is None:
        logger.warning("Cross-encoder model not loaded, skipping reranking")
        return chunks[:top_k]

    try:
        # Prepare pairs for cross-encoder: (query, chunk_text)
        pairs = [(query, chunk["text"]) for chunk in chunks]
        # Get relevance scores from cross-encoder
        scores = cross_encoder.predict(pairs)
        
        # Add re-rank scores to chunks and sort
        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i])
            chunk["reranked"] = True
            
        # Sort by re-rank score (higher is better)
        reranked_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

        # Update relevance_score to be the rerank score for consistency
        for chunk in reranked_chunks:
            chunk["similarity_score"] = chunk["rerank_score"]
            chunk["relevance_score"] = chunk["rerank_score"]

        logger.info(f"Reranked {len(chunks)} chunks, returning top {top_k}")
        return reranked_chunks[:top_k]

    except Exception as e:
        logger.error(f"Error during reranking: {e}")
        # Fall back to original ranking
        return chunks[:top_k]


def build_grounded_context(chunks: List[Dict], include_relevance: bool = True) -> str:
    """
    Build a grounded context string with proper citations.
    Format:
    [Source: filename.pdf, Chunk: 0, Relevance: 0.85]
    Text content...

    [Source: filename.pdf, Chunk: 1, Relevance: 0.78]
    Text content...

    Args:
    - chunks: List of chunk dictionaries
    - include_relevance: Whether to include relevance scores in citations
    Returns:
    - Formatted context string with citations
    """
    context_parts = []
    for chunk in chunks:
        source = chunk.get("source", "Unknown")
        chunk_index = chunk.get("chunk_index", 0)
        text = chunk.get("text", "")
        similarity = chunk.get("similarity_score", 0.0)

        # Format citation header using template function
        if include_relevance and similarity > 0:
            citation_header = format_citation(source, chunk_index, relevance=similarity)
        else:
            citation_header = format_citation(source, chunk_index)

        context_parts.append(f"{citation_header}\n{text}")

    return "\n\n".join(context_parts)


def generate_answer(
    context: str, 
    question: str, 
    temperature: float = 0.1, 
    max_tokens: int = 1000
) -> Tuple[str, Optional[float]]:
    """
    Generate an answer using OpenAI with retrieved context.
    Args:
    - context: Grounded context with citations
    - question: User question
    - temperature: Lower temperature (0.1) for more factual, deterministic responses
    - max_tokens: Maximum tokens in response
    Returns:
    - Tuple of (answer, confidence)
    """
    system_prompt = get_system_prompt()
    user_prompt = format_rag_prompt(context, question)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,  # Very low temperature for factual responses
            max_tokens=max_tokens,  # Configurable max tokens
            top_p=0.9,  # Nucleus sampling for focused responses
        )

        answer = response.choices[0].message.content

        # Calculate confidence based on finish reason
        finish_reason = response.choices[0].finish_reason
        if finish_reason == "stop":
            # Answer completed normally
            confidence = 0.9
        elif finish_reason == "length":
            # Answer was truncated
            confidence = 0.7
        else:
            confidence = 0.5

        # Check if answer is a no-answer response - lower confidence significantly
        if is_no_answer_response(answer):
            confidence = 0.2  # Very low confidence for no-answer responses
        else:
            # Check for uncertainty phrases - moderate confidence reduction
            answer_lower = answer.lower()
            uncertainty_phrases = [
                "uncertain",
                "unclear",
                "may be",
                "might be",
                "possibly",
                "probably",
            ]
            if any(phrase in answer_lower for phrase in uncertainty_phrases):
                confidence = max(0.5, confidence * 0.8)  # Reduce but don't go too low

        return answer, confidence

    except Exception as e:
        raise Exception(f"Error generating answer: {str(e)}")


def extract_citations_from_answer(answer: str, chunks: List[Dict]) -> List[Dict]:
    """
    Extract citation information from the answer.
    Uses regex patterns to find citations in the format [Source: filename, Chunk: N].

    Returns:
    - List of citation dictionaries
    """
    from rag.templates import extract_citations_from_text

    # Use template function for citation extraction
    extracted_citations = extract_citations_from_text(answer)

    # Map extracted citations to chunks for full metadata
    citations = []
    for ext_citation in extracted_citations:
        source = ext_citation["source"]
        chunk_index = ext_citation["chunk_index"]

        # Find matching chunk
        matching_chunk = None
        for chunk in chunks:
            if (
                chunk.get("source", "").lower() == source.lower()
                and chunk.get("chunk_index") == chunk_index
            ):
                matching_chunk = chunk
                break

        if matching_chunk:
            citations.append(
                {
                    "source": matching_chunk.get("source", source),
                    "chunk_index": chunk_index,
                    "chunk_id": matching_chunk.get("chunk_id"),
                    "relevance_score": matching_chunk.get("similarity_score")
                    or matching_chunk.get("relevance_score"),
                    "rerank_score": matching_chunk.get("rerank_score"),
                    "reranked": matching_chunk.get("reranked", False),
                    "text_preview": (
                        matching_chunk.get("text", "")[:200] + "..."
                        if len(matching_chunk.get("text", "")) > 200
                        else matching_chunk.get("text", "")
                    ),
                }
            )

    # If no explicit citations found, return all chunks as potential sources
    if not citations:
        citations = [
            {
                "source": chunk.get("source", "Unknown"),
                "chunk_index": chunk.get("chunk_index", 0),
                "chunk_id": chunk.get("chunk_id"),
                "relevance_score": chunk.get("similarity_score")
                or chunk.get("relevance_score"),
                "rerank_score": chunk.get("rerank_score"),
                "reranked": chunk.get("reranked", False),
                "text_preview": (
                    chunk.get("text", "")[:200] + "..."
                    if len(chunk.get("text", "")) > 200
                    else chunk.get("text", "")
                ),
            }
            for chunk in chunks
        ]

    return citations


def retrieve_and_answer(
    question: str,
    max_results: int = 5,
    temperature: float = 0.1,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    use_reranking: bool = DEFAULT_USE_RERANKING,
    rerank_top_k: int = DEFAULT_RERANK_TOP_K,
) -> Tuple[str, List[Dict], Optional[float], List[Dict]]:
    """
    Retrieve relevant chunks and generate an answer with citations.
    Args:
    - question: User question
    - max_results: Maximum number of chunks to return
    - temperature: Temperature for LLM generation
    - similarity_threshold: Minimum similarity score for chunks (0.0-1.0)
    - use_reranking: Whether to use cross-encoder reranking
    - rerank_top_k: Number of candidates to retrieve for reranking
    Returns:
    - Tuple of (answer, sources, confidence, citations)
    """
    # Retrieve relevant chunks with optional reranking and similarity gating
    chunks = retrieve_relevant_chunks(
        query=question,
        max_results=max_results,
        similarity_threshold=similarity_threshold,
        use_reranking=use_reranking,
        rerank_top_k=rerank_top_k,
    )

    if not chunks:
        # Use template function for consistent no-answer response
        no_answer = get_no_answer_response()
        return (no_answer, [], 0.1, [])  # Very low confidence when no chunks retrieved

    # Build grounded context with citations
    context = build_grounded_context(chunks)

    # Generate answer
    answer, confidence = generate_answer(context, question, temperature=temperature)

    # Prepare sources (all retrieved chunks)
    sources = [
        {
            "source": chunk.get("source", "Unknown"),
            "chunk_index": chunk.get("chunk_index", -1),
            "chunk_id": chunk.get("chunk_id"),
            "similarity_score": chunk.get("similarity_score"),
            "relevance_score": chunk.get("similarity_score") or chunk.get("relevance_score"),
            "rerank_score": chunk.get("rerank_score"),
            "reranked": chunk.get("reranked", False),
            "initial_rank": chunk.get("initial_rank"),
            "distance": chunk.get("distance"),
            "text_preview": (
                chunk.get("text", "")[:150] + "..."
                if len(chunk.get("text", "")) > 150
                else chunk.get("text", "")
            ),
        }
        for chunk in chunks
    ]

    # Extract citations from answer
    citations = extract_citations_from_answer(answer, chunks)

    return answer, sources, confidence, citations


if __name__ == "__main__":
    question = "What are the symptoms and treatments of HIV?"
    answer, sources, confidence, citations = retrieve_and_answer(question)
    print("\n=== ANSWER ===")
    print(answer)
    print("\n=== CONFIDENCE ===", confidence)
    print("\n=== SOURCES ===")
    for s in sources:
        print(
            f"- {s['source']} (chunk {s['chunk_index']}, sim={s['similarity_score']:.3f})"
        )
