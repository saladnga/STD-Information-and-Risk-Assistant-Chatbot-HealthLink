"""
Chat business logic: the system prompt, RAG lookups (for regular chat and for a confirmed diagnosis), the ML prediction call, and the analysis prompt.
Kept separate from routers/chat.py so the WebSocket handler only has to orchestrate these steps, not implement them.
"""

import sys
import os
import asyncio
import logging
from typing import Optional, Dict, Tuple

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from knowledge_base import STD_KNOWLEDGE
from rag.retriever import retrieve_and_answer
from model import process_text_to_feature

logger = logging.getLogger(__name__)


def build_system_prompt(user_profile: Optional[Dict]) -> str:
    """Build the personalized system prompt for a chat session"""
    base_prompt = """
    You are Troy HealthBot, a compassionate health assistant specializing in sexual health.
    You have access to comprehensive medical literature and evidence-based resources.
    """
    # Add user-specific context if available
    if user_profile:
        user_context = f"\n\nUser Context:"
        if user_profile.get("first_name"):
            user_context += f"\n- Name: {user_profile['first_name']}"
        if user_profile.get("gender"):
            gender = user_profile["gender"].lower()
            if gender in ["male", "man", "m"]:
                user_context += f"\n- Gender: Male (use he/him pronouns)"
            elif gender in ["female", "woman", "f"]:
                user_context += f"\n- Gender: Female (use she/her pronouns)"
            elif gender in ["non-binary", "nonbinary", "nb"]:
                user_context += f"\n- Gender: Non-binary (use they/them pronouns)"
            elif gender in ["transgender"]:
                user_context += (
                    f"\n- Gender: Transgender (ask for preferred pronouns if needed)"
                )
            elif gender in ["other"]:
                user_context += (
                    f"\n- Gender: Other (use they/them pronouns or ask for preference)"
                )
            elif gender in ["prefer-not-to-say"]:
                user_context += (
                    f"\n- Gender: Prefer not to specify (use gender-neutral language)"
                )
            else:
                user_context += (
                    f"\n- Gender: {user_profile['gender']} (use appropriate pronouns)"
                )
        if user_profile.get("year_in_school"):
            user_context += f"\n- Academic Level: {user_profile['year_in_school']}"
        if user_profile.get("date_of_birth"):
            from datetime import datetime

            try:
                birth_date = datetime.strptime(
                    user_profile["date_of_birth"], "%Y-%m-%d"
                )
                age = datetime.now().year - birth_date.year
                user_context += f"\n- Age: ~{age} years old"
            except:
                pass

        base_prompt += user_context

        full_prompt = (
            base_prompt
            + """
            Your approach:
            1. Greet users warmly by name (if available) and ask about their concerns
            2. Use appropriate pronouns based on their gender identity
            3. If symptoms are unclear, ask clarifying questions about:
            - Discharge (color: white/gray/yellow/green)
            - Pain/burning location and severity
            - Unusual odors
            - Duration of symptoms
            4. Once you have enough information, say: "Let me analyze your symptoms..."
            5. Be empathetic, non-judgemental, and medically responsible
            6. Always encourage professional medical consultation
            7. When providing information from medical proper citations using [Source: filename, Chunk: X] format
            8. Distinguish between general medical known-sourced information
            9. For document-sourced facts: Use citation fact
            10. For general knowledge: You may mention your general knowledge to clarify the source
            Important: You gather information through to analyze, signal with "ANALYZE:" prefix.
            """
        )

    return full_prompt


async def get_rag_context_for_chat(message_content: str) -> str:
    """Retrieve RAG context for a regular chat message, formatted for prompt injection."""
    logger.debug(f"\nREGULAR CHAT MESSAGE")
    logger.debug(f"User input: '{message_content[:100]}...'")

    try:
        logger.debug(f"Attempting RAG retrieval for chat context...")
        rag_answer, rag_sources, rag_confidence, rag_citations = (
            await asyncio.to_thread(
                retrieve_and_answer,
                question=message_content,
                max_results=3,
                temperature=0.1,
            )
        )

        if rag_answer and rag_confidence and rag_confidence > 0.3:
            logger.debug(f"RAG CONTEXT FOUND")
            logger.debug(f"Sources: {len(rag_sources) if rag_sources else 0}")
            logger.debug(f"Confidence: {rag_confidence}")

            # Format citations more prominently
            citation_text = ""
            if rag_citations:
                citations_list = []
                for citation in rag_citations:
                    if isinstance(citation, dict):
                        filename = citation.get(
                            "source", citation.get("filename", "Unknown")
                        )
                        chunk = citation.get(
                            "chunk_index", citation.get("chunk", "N/A")
                        )
                        citations_list.append(f"[Source: {filename}, Chunk: {chunk}]")
                    else:
                        citations_list.append(str(citation))
                citation_text = f"\n\nCITATIONS TO USE: {'; '.join(citations_list)}"

            return f"\n\nMEDICAL DOCUMENT CONTEXT:\n{rag_answer}{citation_text}\n\nIMPORTANT: This information comes from medical documents and MUST be cited when used!"

        logger.debug(f"NO RAG CONTEXT - Using general medical knowledge")
        logger.debug(
            f"Reason: answer={bool(rag_answer)}, confidence={rag_confidence}"
        )

        return ""

    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return ""


async def run_ml_prediction(
    symptom_text: str,
    model,
    label_encoder,
    feature_columns
) -> Tuple[str, float, Dict]:
    """Run XGBoost prediction on extracted symptom features."""
    feature_dict = process_text_to_feature(symptom_text, feature_columns)
    feature_df = pd.DataFrame([feature_dict], columns=feature_columns)
    prediction_probability = await asyncio.to_thread(model.predict_proba, feature_df)
    prediction_class = await asyncio.to_thread(model.predict, feature_df)
    prediction_class_name = label_encoder.inverse_transform(prediction_class)[0]
    class_probability = dict(
        zip(label_encoder.classes_, prediction_probability[0].tolist())
    )
    confidence = class_probability[prediction_class_name] * 100
    return prediction_class_name, confidence, class_probability


async def get_rag_context_for_diagnosis(
    prediction_class_name: str, symptoms_text: str
) -> Tuple[str, list, str, Dict]:
    """
    Retrieve RAG context for the predicted condition, falling back to the built-in knowledge base when no real document chunks are found.
    Returns (medical_info, rag_sources, context_source, primary_info).
    """
    rag_query = f"What is {prediction_class_name}? Symptoms, treatment, causes, and medical information about {prediction_class_name}. User symptoms: {symptoms_text}"

    logger.debug(f"\nATTEMPTING RAG RETRIEVAL")
    logger.debug(f"Query: '{rag_query}'")
    logger.debug(f"Predicted condition: {prediction_class_name}")

    rag_answer, rag_sources, rag_confidence, rag_citations = await asyncio.to_thread(
        retrieve_and_answer,
        question=rag_query,
        max_results=5,  # Retrieve more documents for comprehensive information
    )

    logger.debug(f"RAG RESULTS:")
    logger.debug(f"Answer available: {bool(rag_answer and rag_answer.strip())}")
    logger.debug(f"Confidence: {rag_confidence}")
    logger.debug(f"Sources found: {len(rag_sources) if rag_sources else 0}")

    if rag_sources:
        for i, source in enumerate(rag_sources[:3], 1):
            filename = source.get("source", source.get("filename", "Unknown"))
            logger.debug(f"      Source {i}: {filename}")

    primary_info = STD_KNOWLEDGE.get(prediction_class_name, {})

    # Check rag_sources, not just rag_answer's truthiness - retrieve_and_answer always returns non-empty text (a "no answer" template) even when zero chunks matched, so checking the answer's text alone can never detect a genuine "nothing found" case. rag_sources is empty precisely when that happens.
    if rag_sources:
        logger.debug(
            f"USING RAG CONTEXT - Retrieved information from medical documents"
        )
        medical_info = f"RAG-Retrieved Information:\n{rag_answer}"
        context_source = "RAG Documents"

        if rag_citations:
            citation_strings = []
            for citation in rag_citations:
                source = citation.get("source", "Unknown")
                chunk_index = citation.get("chunk_index", 0)
                citation_strings.append(f"{source} (chunk {chunk_index})")

            medical_info += f"\n\nSource Citations: {', '.join(citation_strings)}"
    else:
        logger.debug(f"FALLBACK TO KNOWLEDGE BASE - No suitable RAG content found")
        logger.debug(
            f"Reason: Empty answer={not rag_answer}, Low confidence={rag_confidence}"
        )
        context_source = "Built-in Knowledge Base"

        medical_info = f"""
        - Description: {primary_info.get('description', '')}
        - Common symptoms: {', '.join(primary_info.get('symptoms', [])[:4])}
        - Treatment: {primary_info.get('treatment', '')}
        - Urgency: {primary_info.get('urgency', 'moderate')}
        """

    return medical_info, rag_sources, context_source, primary_info


def build_analysis_prompt(
    prediction_class_name: str,
    confidence: float,
    context_source: str,
    medical_info: str,
    rag_sources: list,
    primary_info: Dict,
) -> str:
    """Build the analysis prompt summarizing the ML prediction and medical context for GPT."""
    logger.debug(f"GENERATING GPT RESPONSE")
    logger.debug(f"Context Source: {context_source}")
    logger.debug(f"ML Prediction: {prediction_class_name} ({confidence:.1f}%)")

    return f"""
            Based on the conversation, here are the analysis results:
            PREDICTION: {primary_info.get('full_name', prediction_class_name)}
            CONFIDENCE: {confidence:.1f}%
            CONTEXT SOURCE: {context_source}
            MEDICAL INFO: {medical_info} {f"SOURCES: {', '.join([source.get('source', 'Unknown') for source in rag_sources])}" if rag_sources else ""}
            Generate a compassionate response (150-200 words) that:
            1. Explains what this condition is in simple terms
            2. Relates it to their specific symptoms mentioned
            3. Discusses treatment options based on the retrieved information
            4. Advises next steps (see doctor within X timeframe)
            5. Offers to answer any questions they have
            6. If sources are available, cite ONLY the exact document names listed in the SOURCES section above - never add any other source, organization, or publication not listed there, even a well-known one
            7. If no SOURCES section is present above, this information comes from general medical knowledge - say so explicitly, and do NOT name any specific organization, clinic, or publication (e.g. Mayo Clinic, CDC, WHO) as a source, since none was actually retrieved
            Be warm, reassuring, but medically responsible. Include actual source names only if a SOURCES section was provided above - never invent one.
            """
