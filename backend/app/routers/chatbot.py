from fastapi import (
    WebSocket,
    WebSocketDisconnect,
    APIRouter,
    Query,
    HTTPException,
    Header,
)
import uuid
import re
import json
from openai import AsyncOpenAI
import asyncio
from dotenv import load_dotenv
from routers.utils import (
    verify_user_token,
    get_or_create_session,
    load_chat_history,
    save_message,
    update_session_title,
    get_user_session,
)
import pandas as pd
import sys
import os
from supabase_client import get_supabase_client

# Add parent directory to path for knowledge_base import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from knowledge_base import STD_KNOWLEDGE
from rag.retriever import retrieve_and_answer
from model import process_text_to_feature

# Global to load in lifespan
model = None
nlp = None
label_encoder = None


# Setup environment for OpenAI API
load_dotenv()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Store active chat sessions (WebSocket)
# chat_sessions = {}
active_connections = {}


router = APIRouter(prefix="/ws", tags=["WebSocket Chat"])


# WebSocket Endpoint: Interactive Health Chat
@router.websocket("/chat")
async def health_chat(
    websocket: WebSocket, token: str = Query(...), session_id: str = Query(None)
):
    """
    Real-time interactive chatbot with persistent storage.

    Query Parameters:
    - token: JWT access token from Supabase auth
    - session_id: (Optional) UUID of existing session to resume

    Workflow:
    1. Authenticate user via token
    2. Load or create chat session in database
    3. Load chat history if resuming
    4. Stream messages and save to database
    5. Trigger ML analysis when appropriate
    """

    # Get model components from app state
    model = websocket.app.state.model
    nlp = websocket.app.state.nlp
    label_encoder = websocket.app.state.label_encoder

    user = verify_user_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = user["id"]

    await websocket.accept()

    try:
        # Use the session_id from query parameter if provided, otherwise create new
        # Pass the JWT token to get_or_create_session so Supabase client can set
        # the auth session and satisfy RLS policies during inserts.
        session = get_or_create_session(user_id, session_id, token)
        current_session_id = session["id"]
    except Exception as e:
        await websocket.send_text(f"Error loading session: {str(e)}")
        await websocket.close()
        return

    # session_id = str(uuid.uuid4())

    chat_history = load_chat_history(current_session_id)

    # Get user profile for personalized interactions
    user_profile = None
    try:
        supabase = get_supabase_client()
        profile_result = (
            supabase.table("user_profiles")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if profile_result.data:
            user_profile = profile_result.data
    except Exception as e:
        print(f"Warning: Could not load user profile: {e}")

    # Create personalized system prompt
    base_prompt = """You are Troy HealthBot, a compassionate health assistant specializing in sexual health.
You have access to comprehensive medical literature and evidence-based resources."""

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
7. When providing information from medical literature, always include proper citations using [Source: filename, Chunk: X] format
8. Distinguish between general medical knowledge and specific document-sourced information
9. For document-sourced facts: Use citations immediately after each fact
10. For general knowledge: You may mention "Based on general medical knowledge" to clarify the source

Important: You gather information through conversation. When ready to analyze, signal with "ANALYZE:" prefix."""
    )

    # Initialize conversation memory
    messages = {
        "messages": [
            {
                "role": "system",
                "content": full_prompt,
            }
        ],
        "collected_symptoms": {},
        "needs_analysis": False,
        "user_profile": user_profile,  # Store for later use
    }

    for msg in chat_history:
        # chat_history entries come from DB; append into the messages list
        messages["messages"].append(
            {
                "role": msg["role"],
                "content": msg["content"],
            }
        )

    active_connections[current_session_id] = {
        "websocket": websocket,
        "user_id": user_id,
        "messages": messages,
        "message_count": len(chat_history),
    }

    try:
        while True:
            user_input = await websocket.receive_text()

            # Append user message to DB and in-memory messages list
            save_message(current_session_id, user_id, "user", user_input, token)

            messages["messages"].append({"role": "user", "content": user_input})

            # First try to get RAG context for the user's question
            rag_context = ""
            message_content = user_input.strip()

            print(f"\nREGULAR CHAT MESSAGE")
            print(f"   User input: '{message_content[:100]}...'")

            try:
                # Try RAG retrieval for additional context
                print(f"Attempting RAG retrieval for chat context...")
                rag_answer, rag_sources, rag_confidence, rag_citations = await asyncio.to_thread(
                    retrieve_and_answer,
                    question=message_content, max_results=3, temperature=0.1
                )

                if rag_answer and rag_confidence and rag_confidence > 0.3:
                    print(f"   RAG CONTEXT FOUND")
                    print(f"   Sources: {len(rag_sources) if rag_sources else 0}")
                    print(f"   Confidence: {rag_confidence}")

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
                                citations_list.append(
                                    f"[Source: {filename}, Chunk: {chunk}]"
                                )
                            else:
                                citations_list.append(str(citation))
                        citation_text = (
                            f"\n\nCITATIONS TO USE: {'; '.join(citations_list)}"
                        )

                    # Use templates.py formatting for better consistency
                    rag_context = f"\n\nMEDICAL DOCUMENT CONTEXT:\n{rag_answer}{citation_text}\n\nIMPORTANT: This information comes from medical documents and MUST be cited when used!"
                else:
                    print(f"NO RAG CONTEXT - Using general medical knowledge")
                    print(
                        f"   Reason: answer={bool(rag_answer)}, confidence={rag_confidence}"
                    )

            except Exception as e:
                print(f"RAG retrieval failed: {e}")

            # Add system context if we have RAG information
            enhanced_messages = messages["messages"].copy()
            if rag_context:
                # Import RAG citation guidelines from templates
                from rag.templates import format_citation

                system_context = f"""You are Troy HealthBot, a helpful health assistant. Use the following medical information to enhance your response if relevant: {rag_context}

CRITICAL RAG CITATION RULES (follow these strictly):
1. MANDATORY CITATIONS: When you use ANY information from the medical documents above, you MUST include the exact source citation
2. CITATION FORMAT: Use the format [Source: filename.pdf, Chunk: X] immediately after each document-sourced fact
3. EXAMPLE: "Chlamydia is commonly treated with antibiotics [Source: medical_guide.pdf, Chunk: 15]."
4. DISTINCTION: Clearly distinguish between:
   - Information from documents (MUST cite with [Source: filename, Chunk: X])
   - Your general medical knowledge (no citation needed, but mention it's general knowledge)
5. ACCURACY: Only use information explicitly stated in the provided context - do not make inferences
6. TRANSPARENCY: If document information is incomplete, state that limitation clearly
7. SAFETY: Always encourage professional medical consultation for diagnosis and treatment

Remember: Patient safety depends on accurate sourcing. When in doubt about document content, say so explicitly."""
                enhanced_messages.insert(
                    -1, {"role": "system", "content": system_context}
                )

            # Stream OpenAI GPT response
            analysis_will_trigger = False  # Initialize
            try:
                # The OpenAI client expects a list of message dicts
                res = await openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=enhanced_messages,
                    temperature=0.7,
                    stream=True,
                )

                ai_response = ""
                async for chunk in res:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        ai_response += content
                        # Only stream to frontend if we're not going to trigger analysis
                        # (we'll check this after the response is complete)
                    # Check if streaming is complete
                    if chunk.choices[0].finish_reason is not None:
                        break

                # Check if analysis will be triggered before sending response
                analysis_will_trigger = (
                    "ANALYZE:" in ai_response
                    or "analyze your symptoms" in ai_response.lower()
                )

                # Only send response to frontend if analysis won't be triggered
                if not analysis_will_trigger:
                    # Send the complete response at once
                    if ai_response.strip():
                        await websocket.send_text(ai_response)
                    else:
                        fallback = (
                            "I'm here if you'd like to share more or ask a question."
                        )
                        await websocket.send_text(fallback)
                        ai_response = fallback
                    # Send completion signal to close stream
                    await websocket.send_text("\n")
                else:
                    # Analysis will be triggered, so don't send regular response
                    print(
                        "Analysis will be triggered - skipping regular response display"
                    )

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                await websocket.send_text(error_msg)
                ai_response = error_msg
                analysis_will_trigger = False  # No analysis on error

            # Use the analysis check we did earlier
            analysis_triggered = analysis_will_trigger

            # Only save regular response if analysis won't be triggered
            # (analysis will save its own comprehensive response)
            if not analysis_triggered:
                save_message(
                    current_session_id, user_id, "assistant", ai_response, token
                )

            # Trigger analysis if GPT signal readiness
            if analysis_triggered:
                # Check if model is available
                if not model or not label_encoder:
                    await websocket.send_text(
                        "\n\n **Analysis Error**: The ML model is not available. Please contact support or try again later.\n"
                    )
                    continue

                # Combine user message into symptom text
                symptom_text = " ".join(
                    [
                        msg["content"]
                        for msg in messages["messages"]
                        if msg["role"] == "user"
                    ]
                )

                # Run ML-based prediction
                feature_columns = getattr(websocket.app.state, "feature_columns", None)
                if not feature_columns:
                    # Fallback: load from feature specification
                    from model import load_feature_spec

                    feature_columns = load_feature_spec() or []
                    if not feature_columns:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "role": "assistant",
                                    "content": "⚠️ Model features not available. Please ensure the model is trained.",
                                    "type": "error",
                                }
                            )
                        )
                        continue

                feature_dict = process_text_to_feature(symptom_text, feature_columns)
                feature_df = pd.DataFrame([feature_dict], columns=feature_columns)
                prediction_probability = await asyncio.to_thread(model.predict_proba, feature_df)
                prediction_class = await asyncio.to_thread(model.predict, feature_df)
                prediction_class_name = label_encoder.inverse_transform(
                    prediction_class
                )[0]
                class_probability = dict(
                    zip(label_encoder.classes_, prediction_probability[0].tolist())
                )

                # Retrieve medical information using RAG
                confidence = class_probability[prediction_class_name] * 100

                # Create a detailed query for RAG retrieval
                symptoms_text = " ".join(
                    [
                        msg["content"]
                        for msg in messages["messages"][-5:]
                        if msg["role"] == "user"
                    ]
                )
                rag_query = f"What is {prediction_class_name}? Symptoms, treatment, causes, and medical information about {prediction_class_name}. User symptoms: {symptoms_text}"

                # First ask GPT to query RAG for additional context
                print(f"\nATTEMPTING RAG RETRIEVAL")
                print(f"   Query: '{rag_query}'")
                print(f"   Predicted condition: {prediction_class_name}")

                # Get comprehensive information from RAG system
                rag_answer, rag_sources, rag_confidence, rag_citations = await asyncio.to_thread(
                    retrieve_and_answer,
                    question=rag_query,
                    max_results=5,  # Retrieve more documents for comprehensive information
                    
                )

                print(f"RAG RESULTS:")
                print(f"   Answer available: {bool(rag_answer and rag_answer.strip())}")
                print(f"   Confidence: {rag_confidence}")
                print(f"   Sources found: {len(rag_sources) if rag_sources else 0}")
                if rag_sources:
                    for i, source in enumerate(rag_sources[:3], 1):
                        filename = source.get(
                            "source", source.get("filename", "Unknown")
                        )
                        print(f"      Source {i}: {filename}")

                # Fallback to hardcoded knowledge if RAG fails
                primary_info = STD_KNOWLEDGE.get(prediction_class_name, {})

                # Use RAG answer if available, otherwise fall back to structured info
                if rag_answer and rag_answer.strip():
                    print(
                        f"USING RAG CONTEXT - Retrieved information from medical documents"
                    )
                    medical_info = f"RAG-Retrieved Information:\n{rag_answer}"
                    context_source = "RAG Documents"

                    if rag_citations:
                        # Format citations as readable strings
                        citation_strings = []
                        for citation in rag_citations:
                            source = citation.get("source", "Unknown")
                            chunk_index = citation.get("chunk_index", 0)
                            citation_strings.append(f"{source} (chunk {chunk_index})")

                        medical_info += (
                            f"\n\nSource Citations: {', '.join(citation_strings)}"
                        )
                else:
                    print(
                        f"FALLBACK TO KNOWLEDGE BASE - No suitable RAG content found"
                    )
                    print(
                        f"   Reason: Empty answer={not rag_answer}, Low confidence={rag_confidence}"
                    )
                    context_source = "Built-in Knowledge Base"

                    # Fallback to structured knowledge
                    medical_info = f"""- Description: {primary_info.get('description', '')}
                        - Common symptoms: {', '.join(primary_info.get('symptoms', [])[:4])}
                        - Treatment: {primary_info.get('treatment', '')}
                        - Urgency: {primary_info.get('urgency', 'moderate')}"""

                # Construct medical summary for GPT to rephrase empathetic
                print(f"🤖 GENERATING GPT RESPONSE")
                print(f"   Context Source: {context_source}")
                print(f"   ML Prediction: {prediction_class_name} ({confidence:.1f}%)")

                analysis_prompt = f"""Based on the conversation, here are the analysis results:
                PREDICTION: {primary_info.get('full_name', prediction_class_name)}
                CONFIDENCE: {confidence:.1f}%
                CONTEXT SOURCE: {context_source}
                
                MEDICAL INFO:
                {medical_info}
                
                {f"SOURCES: {', '.join([source.get('source', 'Unknown') for source in rag_sources])}" if rag_sources else ""}
                
                Generate a compassionate response (150-200 words) that:
                1. Explains what this condition is in simple terms
                2. Relates it to their specific symptoms mentioned
                3. Discusses treatment options based on the retrieved information
                4. Advises next steps (see doctor within X timeframe)
                5. Offers to answer any questions they have
                6. If sources are available, specifically mention the source documents by name from the SOURCES section
                Be warm, reassuring, but medically responsible. Include actual source names if provided.
                """

                messages["messages"].append(
                    {"role": "system", "content": analysis_prompt}
                )

                # Stream empathetic final analysis message
                final_res = await openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    # model="gpt-5-mini",
                    messages=messages["messages"],
                    temperature=0.7,
                    stream=True,
                )

                final_response = ""
                await websocket.send_text("\n\n")
                async for chunk in final_res:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        final_response += content
                        await websocket.send_text(chunk.choices[0].delta.content)
                    # Check if streaming is complete
                    if chunk.choices[0].finish_reason is not None:
                        break

                # Add source information if available from RAG
                if rag_sources and len(rag_sources) > 0:
                    sources_text = "\n\n**Sources:**\n"
                    for i, source in enumerate(
                        rag_sources[:3], 1
                    ):  # Show up to 3 sources
                        # Try multiple keys for the source filename
                        filename = source.get(
                            "source", source.get("filename", "Medical Literature")
                        )
                        # page = source.get("page", source.get("page_number", "N/A"))
                        sources_text += f"{i}. {filename} \n"
                        print(f"📚 Source {i}: {filename}")

                    await websocket.send_text(sources_text)
                    final_response += sources_text

                # Send completion signal for analysis response
                await websocket.send_text("\n")

                # Save AI reply with sources
                save_message(
                    current_session_id, user_id, "assistant", final_response, token
                )
                messages["messages"].append(
                    {"role": "assistant", "content": final_response}
                )

                # Update session title if it's a new conversation
                if (
                    current_session_id in active_connections
                    and active_connections[current_session_id]["message_count"] <= 5
                ):
                    title = f"Health Consultation - {prediction_class_name}"
                    update_session_title(current_session_id, title)
            else:
                # Regular response (not analysis) - append to messages only
                # (message already saved above if no analysis was triggered)
                messages["messages"].append(
                    {"role": "assistant", "content": ai_response}
                )

            # Safely update message count
            if current_session_id in active_connections:
                active_connections[current_session_id]["message_count"] += 1

    except WebSocketDisconnect:
        # Clean up session on disconnect
        # Use the current_session_id we created for this connection
        if current_session_id in active_connections:
            del active_connections[current_session_id]
        # Don't call websocket.close() here - it's already closed and causes AttributeError


@router.get("/sessions")
async def list_sessions(user_id: str, authorization: str = Header(...)):
    """
    Get list of user's chat sessions.
    Requires Bearer token in Authorization header.
    """
    # Extract token from "Bearer <token>" or handle raw token
    try:
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
        else:
            token = authorization
    except AttributeError:
        raise HTTPException(
            status_code=401, detail="Invalid authorization header format"
        )

    # Verify token
    user = verify_user_token(token)
    if not user or user["id"] != user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    sessions = get_user_session(user_id)
    return sessions


@router.get("/chat-history")
async def get_chat_history(
    session_id: str, user_id: str, authorization: str = Header(...)
):
    """
    Get chat history for a specific session.
    Requires Bearer token in Authorization header.
    """
    # Extract token from "Bearer <token>"
    token = authorization.replace("Bearer ", "")

    # Verify token
    user = verify_user_token(token)
    if not user or user["id"] != user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Load chat history
    history = load_chat_history(session_id)
    return history


@router.put("/sessions/{session_id}/title")
async def update_session_title_endpoint(
    session_id: str, title_data: dict, authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "")
    user = verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # basic validation for payload
    if not title_data or "title" not in title_data:
        raise HTTPException(status_code=400, detail="Missing 'title' in request body")

    supabase = get_supabase_client()
    # verify session exists and belongs to user
    session_check = (
        supabase.table("chat_sessions")
        .select("user_id")
        .eq("id", session_id)
        .execute()
    )

    if not session_check.data or session_check.data[0]["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update the correct table name (chat_sessions)
    result = (
        supabase.table("chat_sessions")
        .update({"title": title_data["title"]})
        .eq("id", session_id)
        .execute()
    )

    # If Supabase returned an error, surface it
    if getattr(result, "error", None):
        raise HTTPException(status_code=500, detail=str(result.error))

    return {"message": "Title updated successfully"}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, authorization: str = Header(...)):
    """Delete a chat session and all its messages."""
    try:
        token = authorization.replace("Bearer ", "")
        user = verify_user_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        supabase = get_supabase_client()

        # Verify the session belongs to the user
        session_check = (
            supabase.table("chat_sessions")
            .select("user_id")
            .eq("id", session_id)
            .single()
            .execute()
        )

        if not session_check.data or session_check.data["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Session not found")

        # Delete all messages first (due to foreign key constraint)
        messages_result = (
            supabase.table("chat_messages")
            .delete()
            .eq("session_id", session_id)
            .execute()
        )

        # Delete the session
        session_result = (
            supabase.table("chat_sessions").delete().eq("id", session_id).execute()
        )

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        )
