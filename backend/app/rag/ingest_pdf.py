"""
PDF ingestion for RAG.
Parses PDFs, chunks text, creates embeddings, and stores in vector database.
Supports both text-based PDFs and scanned/image-based PDFs using OCR.
"""

import os
import logging
from typing import List, Dict
from dotenv import load_dotenv
import pdf2image
import pypdf as PyPDF2
import pytesseract

from openai import OpenAI

# LangChain community modules (mới)
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings


# Vector database
import chromadb
from chromadb.config import Settings

load_dotenv()


# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# PDF text extraction libraries
try:
    import PyPDF2

    PDF_LIBRARY = "PyPDF2"
except ImportError:
    # Fallback to pypdf if PyPDF2 is not available
    try:
        import pypdf as PyPDF2

        PDF_LIBRARY = "pypdf"
    except ImportError:
        PDF_LIBRARY = None
        logger.warning("PyPDF2/pypdf not available. PDF text extraction will not work.")

# OCR libraries (optional)
OCR_AVAILABLE = False
try:
    import pytesseract
    from pdf2image import convert_from_path

    OCR_AVAILABLE = True
    logger.info("OCR libraries (pytesseract, pdf2image) available")
except ImportError:
    logger.warning(
        "OCR libraries not available. Install with: pip install pytesseract pdf2image"
    )
    logger.warning(
        "Also install Tesseract OCR: https://github.com/tesseract-ocr/tesseract"
    )

# Initialize ChromaDB
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
chroma_dir = os.path.join(current_dir, "data", "chroma")
os.makedirs(chroma_dir, exist_ok=True)

client = chromadb.PersistentClient(
    path=chroma_dir, settings=Settings(anonymized_telemetry=False)
)
collection = client.get_or_create_collection(name="medical_documents")


def extract_text_with_ocr(pdf_path: str, dpi: int = 300) -> str:
    """
    Extract text from PDF using OCR (for scanned/image-based PDFs).

    Args:
        pdf_path: Path to PDF file
        dpi: DPI for image conversion (higher = better quality, slower)

    Returns:
        Extracted text from all pages
    """
    if not OCR_AVAILABLE:
        raise ImportError(
            "OCR libraries not available. Install with: "
            "pip install pytesseract pdf2image and install Tesseract OCR"
        )

    text = ""
    try:
        logger.info(f"Converting PDF to images for OCR (DPI: {dpi})...")
        # Convert PDF pages to images
        images = convert_from_path(pdf_path, dpi=dpi)
        logger.info(f"Converted {len(images)} pages to images")

        # Extract text from each image using OCR
        for i, image in enumerate(images):
            logger.debug(f"Processing page {i+1}/{len(images)} with OCR...")
            page_text = pytesseract.image_to_string(image, lang="eng")
            text += f"\n--- Page {i+1} ---\n{page_text}\n"

        logger.info(f"OCR extraction completed. Extracted {len(text)} characters")
        return text.strip()

    except Exception as e:
        raise Exception(f"Error extracting text with OCR: {str(e)}")


def extract_text_from_pdf(
    pdf_path: str, use_ocr: bool = False, ocr_fallback: bool = True, ocr_dpi: int = 300
) -> str:
    """
    Extract text from a PDF file.

    Args:
        pdf_path: Path to PDF file
        use_ocr: If True, use OCR directly (skip text extraction)
        ocr_fallback: If True, fall back to OCR if text extraction yields little/no text
        ocr_dpi: DPI for OCR image conversion (if OCR is used)

    Returns:
        Extracted text from all pages
    """
    text = ""

    # Try text extraction first (unless OCR is explicitly requested)
    if not use_ocr and PDF_LIBRARY:
        try:
            logger.info("Attempting text extraction from PDF...")
            with open(pdf_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                logger.info(f"PDF has {num_pages} pages")

                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    else:
                        logger.debug(f"Page {page_num + 1} returned no text")

            # Check if we got meaningful text
            text_length = len(text.strip())
            logger.info(f"Extracted {text_length} characters via text extraction")

            # If text extraction yielded little text and OCR fallback is enabled, try OCR
            if text_length < 100 and ocr_fallback and OCR_AVAILABLE:
                logger.warning(
                    f"Text extraction yielded only {text_length} characters. Falling back to OCR..."
                )
                try:
                    ocr_text = extract_text_with_ocr(pdf_path, dpi=ocr_dpi)
                    if len(ocr_text.strip()) > text_length:
                        logger.info(
                            f"OCR extracted {len(ocr_text)} characters (more than text extraction)"
                        )
                        return ocr_text
                    else:
                        logger.warning(
                            "OCR did not extract more text. Using text extraction result."
                        )
                except Exception as ocr_error:
                    logger.warning(
                        f"OCR fallback failed: {ocr_error}. Using text extraction result."
                    )

            if text_length > 0:
                return text.strip()
            else:
                raise Exception("Text extraction returned no text")

        except Exception as e:
            logger.warning(f"Text extraction failed: {e}")
            if not ocr_fallback or not OCR_AVAILABLE:
                raise Exception(f"Error extracting text from PDF: {str(e)}")
            # Fall through to OCR

    # Use OCR if explicitly requested or as fallback
    if use_ocr or (ocr_fallback and OCR_AVAILABLE):
        if not OCR_AVAILABLE:
            raise ImportError(
                "OCR requested but libraries not available. Install with: "
                "pip install pytesseract pdf2image and install Tesseract OCR"
            )
        logger.info("Using OCR for text extraction...")
        return extract_text_with_ocr(pdf_path, dpi=ocr_dpi)

    # If we get here, text extraction failed and OCR is not available
    raise Exception(
        "Could not extract text from PDF. Text extraction failed and OCR is not available. "
        "Install OCR libraries: pip install pytesseract pdf2image"
    )


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    words = text.split()

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)

    return chunks


def create_embeddings(texts: List[str]) -> List[List[float]]:
    """Create embeddings for texts using OpenAI."""
    embeddings = []
    for text in texts:
        response = openai_client.embeddings.create(
            model="text-embedding-ada-002", input=text
        )
        embeddings.append(response.data[0].embedding)
    return embeddings


def ingest_pdf(
    pdf_path: str,
    use_ocr: bool = False,
    ocr_fallback: bool = True,
    ocr_dpi: int = 300,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> Dict:
    """
    Ingest a PDF: extract, chunk, embed, and store in vector database.

    Args:
        pdf_path: Path to PDF file
        use_ocr: If True, use OCR directly (skip text extraction)
        ocr_fallback: If True, fall back to OCR if text extraction yields little/no text
        ocr_dpi: DPI for OCR image conversion (higher = better quality, slower)
        chunk_size: Size of text chunks in characters
        chunk_overlap: Overlap between chunks in characters

    Returns:
        dict with number of chunks ingested and extraction method used
    """
    # Extract text (with optional OCR)
    extraction_method = "ocr" if use_ocr else "text"
    try:
        text = extract_text_from_pdf(
            pdf_path, use_ocr=use_ocr, ocr_fallback=ocr_fallback, ocr_dpi=ocr_dpi
        )
        if ocr_fallback and not use_ocr:
            # Check if OCR was actually used (by checking if text length suggests OCR)
            # This is approximate - OCR text tends to have more whitespace
            if len(text) > 1000:  # If we got substantial text, likely OCR was used
                extraction_method = "text_with_ocr_fallback"
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        raise

    if not text or len(text.strip()) < 10:
        raise Exception(
            "Extracted text is too short or empty. PDF may be corrupted or unreadable."
        )

    logger.info(f"Extracted {len(text)} characters using {extraction_method} method")

    # Chunk text
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
    logger.info(f"Created {len(chunks)} chunks from PDF")

    if len(chunks) == 0:
        raise Exception("No chunks created from PDF. Text may be too short.")

    # Create embeddings
    logger.info("Creating embeddings for chunks...")
    embeddings = create_embeddings(chunks)

    # Prepare metadata
    filename = os.path.basename(pdf_path)
    metadatas = [
        {
            "source": filename,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "extraction_method": extraction_method,
        }
        for i in range(len(chunks))
    ]

    # Generate IDs
    ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]

    # Store in ChromaDB
    collection.add(
        embeddings=embeddings, documents=chunks, metadatas=metadatas, ids=ids
    )

    logger.info(f"Successfully ingested {len(chunks)} chunks into vector database")

    return {
        "chunks": len(chunks),
        "filename": filename,
        "extraction_method": extraction_method,
        "text_length": len(text),
    }


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_dir = os.path.join(current_dir, "data", "pdf")

    for filename in os.listdir(pdf_dir):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(pdf_dir, filename)
            print(f"Ingesting {filename}...")
            result = ingest_pdf(pdf_path)
            print(f"{result['chunks']} chunks from {filename} stored successfully!\n")

    print("All PDFs ingested successfully into 'medical_documents' collection!")
