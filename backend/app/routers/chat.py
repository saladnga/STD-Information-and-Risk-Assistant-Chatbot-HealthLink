"""
The live chat WebSocket endpoint. Orchestrates: auth, session load/create, streaming a GPT reply (RAG-grounded when relevant), and - when the model signals it has enough information - running the ML prediction and a second, diagnosis-specific reply. The actual logic for each step lives in services/chat_analysis.py; session/message persistence lives in db.py.
"""

import json
import os
import re
import logging
from contextlib import asynccontextmanager
from openai import AsyncOpenAI
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Query
import asyncio
import limits
from rate_limiter import limiter

from db import (
    verify_user_token,
    get_or_create_session,
    load_chat_history,
    save_message,
    update_session_title,
    get_user_openai_settings,
)
from routers.auth import DEFAULT_CUSTOM_MODEL, ALLOWED_CUSTOM_MODELS
from supabase_client import get_supabase_client
from model import load_feature_spec
from services.chat_analysis import (
    build_system_prompt,
    get_rag_context_for_chat,
    run_ml_prediction,
    get_rag_context_for_diagnosis,
    build_analysis_prompt,
)

logger = logging.getLogger(__name__)

load_dotenv()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Keyed by session_id while a WebSocket is open - in-memory, single-process only
active_connections = {}

router = APIRouter(prefix="/ws", tags=["WebSocket Chat"])

MAX_MESSAGE_LENGTH = 2000  # ~400-500 words
CHAT_RATE_LIMIT = limits.parse("20/minute")

# No personal key: app's key, cheapest model. Personal key: their key, their chosen model (see auth.py's /openai-key, which owns ALLOWED_CUSTOM_MODELS).
DEFAULT_MODEL = "gpt-4o-mini"

KEEPALIVE_INTERVAL_S = 15  # well under typical reverse-proxy idle timeouts


@asynccontextmanager
async def _keepalive(websocket: WebSocket):
    """
    Pings the client every KEEPALIVE_INTERVAL_S seconds for as long as the
    wrapped block runs. A slow RAG lookup or a fully-buffered LLM call (see
    the citation-fix note below) can otherwise leave the socket silent long
    enough for a reverse proxy to decide the connection is dead and drop it
    - the actual cause of a reply that never arrives until a follow-up
    message lands on a freshly-reconnected socket.
    """

    async def ping_loop():
        while True:
            await asyncio.sleep(KEEPALIVE_INTERVAL_S)
            await websocket.send_text("__PING__")

    task = asyncio.create_task(ping_loop())
    try:
        yield
    finally:
        task.cancel()


async def _process_user_message(
    websocket: WebSocket,
    user_input: str,
    current_session_id: str,
    user_id: str,
    token: str,
    messages: dict,
    model,
    label_encoder,
    chat_client: AsyncOpenAI,
    chat_model: str,
):
    """One user message end to end: RAG lookup, the first GPT reply
    (streamed live unless it's an ANALYZE: trigger), and - when triggered -
    the ML prediction plus a diagnosis-specific second reply."""
    # Append user message to DB and in-memory messages list
    await save_message(current_session_id, user_id, "user", user_input, token)

    # First message of a new session: title it from what the user actually asked
    if active_connections[current_session_id]["message_count"] == 0:
        words = user_input.strip().split()
        title_word_limit = 6
        title = " ".join(words[:title_word_limit])
        if len(words) > title_word_limit:
            title += "…"
        if title:
            await update_session_title(current_session_id, title)

    messages["messages"].append({"role": "user", "content": user_input})

    # First try to get RAG context for the user's question
    message_content = user_input.strip()
    rag_context, rag_sources_for_chat = await get_rag_context_for_chat(
        message_content
    )

    # Add system context if we have RAG information
    enhanced_messages = messages["messages"].copy()
    if rag_context:
        system_context = f"""
        You are Troy HealthBot, a helpful health assistant. The following medical information was retrieved specifically because it's relevant to the user's question - you MUST actually base your answer on it, not just your own general knowledge: {rag_context}
        CRITICAL RAG CITATION RULES (follow these strictly):
        1. MANDATORY CITATIONS: You MUST include the exact source citation for every fact drawn from the medical documents above, inline in your visible reply, every time - not only when the user asks where it came from
        2. CITATION FORMAT: Use the format [Source: filename.pdf, Chunk: X] immediately after each document-sourced fact
        3. EXAMPLE: "Chlamydia is commonly treated with antibiotics [Source: medical_guide.pdf, Chunk: 15]."
        4. DISTINCTION: Clearly distinguish between:
        - Information from documents (MUST cite with [Source: filename, Chunk: X])
        - Your general medical knowledge (no citation needed, but mention it's general knowledge)
        5. ACCURACY: Only use information explicitly stated in the provided context - do not make inferences
        6. TRANSPARENCY: If document information is incomplete, state that limitation clearly
        7. SAFETY: Always encourage professional medical consultation for diagnosis and treatment
        8. NEVER invent or name a source (e.g. CDC, WHO, Mayo Clinic) that isn't in the CITATIONS TO USE list above
        Remember: Patient safety depends on accurate sourcing. When in doubt about document content, say so explicitly.
        """

        enhanced_messages.insert(-1, {"role": "system", "content": system_context})

    # Stream OpenAI GPT response
    ANALYSIS_TRIGGER = "ANALYZE:"
    analysis_will_trigger = False  # Initialize
    try:
        # The OpenAI client expects a list of message dicts
        res = await chat_client.chat.completions.create(
            model=chat_model,
            messages=enhanced_messages,
            temperature=0.7,
            stream=True,
        )

        ai_response = ""
        streaming_live = False
        async for chunk in res:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                ai_response += content

                if streaming_live:
                    # Already committed to showing this reply - relay
                    # each piece to the user as it arrives.
                    await websocket.send_text(content)
                elif len(ai_response) >= len(ANALYSIS_TRIGGER):
                    # Enough buffered to know for sure if this starts
                    # with "ANALYZE:" - decide once, then either relay
                    # live or keep buffering silently.
                    if not ai_response.startswith(ANALYSIS_TRIGGER):
                        streaming_live = True
                        await websocket.send_text(ai_response)
            # Check if streaming is complete
            if chunk.choices[0].finish_reason is not None:
                break

        analysis_will_trigger = ai_response.startswith(ANALYSIS_TRIGGER)

        # Only send response to frontend if analysis won't be triggered
        if not analysis_will_trigger:
            if not streaming_live:
                # Short enough to never cross the live-relay threshold - send it now, one-shot.
                if ai_response.strip():
                    await websocket.send_text(ai_response)
                else:
                    fallback = "I'm here if you'd like to share more or ask a question."
                    await websocket.send_text(fallback)
                    ai_response = fallback

            # A real, backend-built citation list from what was
            # actually retrieved - this reply streamed live, so an
            # inline [Source: ...] the model wrote itself can't be
            # verified/stripped before it's already sent (see
            # build_system_prompt's rule #7 for the prompt-side half
            # of this defense). This block is always accurate even
            # if the model's own inline citation wasn't.
            if rag_sources_for_chat:
                # Multiple retrieved chunks often share one source
                # PDF - list each filename once, not once per chunk.
                filenames = []
                for source in rag_sources_for_chat:
                    filename = source.get(
                        "source", source.get("filename", "Medical Literature")
                    )
                    if filename not in filenames:
                        filenames.append(filename)
                sources_text = "\n\n**Sources:**\n" + "\n".join(
                    f"{i}. {name}" for i, name in enumerate(filenames[:3], 1)
                )
                await websocket.send_text(sources_text)
                ai_response += sources_text

            # Send completion signal to close stream
            await websocket.send_text("__DONE__")
        else:
            # Analysis will be triggered, so don't send regular response
            logger.debug(
                "Analysis will be triggered - skipping regular response display"
            )

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        await websocket.send_text(error_msg)
        ai_response = error_msg
        analysis_will_trigger = False  # No analysis on error

    # Use the analysis check we did earlier
    analysis_triggered = analysis_will_trigger

    # Only save regular response if analysis won't be triggered (analysis will save its own comprehensive response)
    if not analysis_triggered:
        await save_message(current_session_id, user_id, "assistant", ai_response, token)

    # Trigger analysis if GPT signal readiness
    if analysis_triggered:
        # Check if model is available
        if not model or not label_encoder:
            await websocket.send_text(
                "\n\n **Analysis Error**: The ML model is not available. Please contact support or try again later.\n"
            )
            return

        # Combine user message into symptom text
        symptom_text = " ".join(
            [msg["content"] for msg in messages["messages"] if msg["role"] == "user"]
        )

        # Run ML-based prediction
        feature_columns = getattr(websocket.app.state, "feature_columns", None)
        if not feature_columns:
            # Fallback: load from feature specification
            feature_columns = load_feature_spec() or []
            if not feature_columns:
                await websocket.send_text(
                    json.dumps(
                        {
                            "role": "assistant",
                            "content": "Warning: Model features not available. Please ensure the model is trained.",
                            "type": "error",
                        }
                    )
                )
                return

        prediction_class_name, confidence, class_probability = await run_ml_prediction(
            symptom_text, model, label_encoder, feature_columns
        )

        symptoms_text = " ".join(
            [
                msg["content"]
                for msg in messages["messages"][-5:]
                if msg["role"] == "user"
            ]
        )
        medical_info, rag_sources, context_source, primary_info = (
            await get_rag_context_for_diagnosis(prediction_class_name, symptoms_text)
        )

        analysis_prompt = build_analysis_prompt(
            prediction_class_name,
            confidence,
            context_source,
            medical_info,
            rag_sources,
            primary_info,
        )

        messages["messages"].append({"role": "system", "content": analysis_prompt})

        # Stream empathetic final analysis message
        final_res = await chat_client.chat.completions.create(
            model=chat_model,
            messages=messages["messages"],
            temperature=0.7,
            stream=True,
        )

        final_response = ""
        async for chunk in final_res:
            if chunk.choices[0].delta.content is not None:
                final_response += chunk.choices[0].delta.content
            # Check if streaming is complete
            if chunk.choices[0].finish_reason is not None:
                break

        # Buffered, not streamed live: the model sometimes invents a bracket citation (e.g. "[Source: CDC]") even with real sources given, so the full reply is checked before anything reaches the user - real sources are listed deterministically below regardless.
        # Upgrade: flush per sentence instead of the whole reply if that ever matters.
        final_response = re.sub(r"\[Source:[^\]]*\]", "", final_response).strip()
        await websocket.send_text("\n\n")
        await websocket.send_text(final_response)

        # Add source information if available from RAG - one entry
        # per filename, not per chunk (several chunks often share a source).
        if rag_sources and len(rag_sources) > 0:
            filenames = []
            for source in rag_sources:
                filename = source.get(
                    "source", source.get("filename", "Medical Literature")
                )
                if filename not in filenames:
                    filenames.append(filename)
            sources_text = "\n\n**Sources:**\n" + "\n".join(
                f"{i}. {name}" for i, name in enumerate(filenames[:3], 1)
            )
            await websocket.send_text(sources_text)
            final_response += sources_text

        # Send completion signal for analysis response
        await websocket.send_text("__DONE__")

        # Save AI reply with sources
        await save_message(current_session_id, user_id, "assistant", final_response, token)
        messages["messages"].append({"role": "assistant", "content": final_response})
    else:
        # Regular response (not analysis) - append to messages only (message already saved above if no analysis was triggered)
        messages["messages"].append({"role": "assistant", "content": ai_response})

    # Safely update message count
    if current_session_id in active_connections:
        active_connections[current_session_id]["message_count"] += 1


@router.websocket("/chat")
async def health_chat(
    websocket: WebSocket,
    token: str = Query(...),
    session_id: str = Query(None)
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
    label_encoder = websocket.app.state.label_encoder

    user = await verify_user_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = user["id"]

    # Decided once per connection, not per message - a user's key/model choice doesn't change mid-conversation.
    user_openai_key, user_openai_model = await get_user_openai_settings(user_id)
    if user_openai_key:
        chat_client = AsyncOpenAI(api_key=user_openai_key)
        # Guards against a stale/invalid stored value (e.g. the allowed list changed after this was saved) rather than trusting the DB blindly.
        chat_model = (
            user_openai_model
            if user_openai_model in ALLOWED_CUSTOM_MODELS
            else DEFAULT_CUSTOM_MODEL
        )
    else:
        chat_client = openai_client
        chat_model = DEFAULT_MODEL

    await websocket.accept()

    try:
        # Use the session_id from query parameter if provided, otherwise create new
        session = await get_or_create_session(user_id, session_id, token)
        current_session_id = session["id"]

        # The client has no way to know a brand-new session's id otherwise - without this, refreshing a "new chat" spawns a second, orphaned session.
        await websocket.send_text(f"__SESSION__:{current_session_id}")
    except Exception as e:
        await websocket.send_text(f"Error loading session: {str(e)}")
        await websocket.close()
        return

    chat_history = await load_chat_history(current_session_id)

    # Get user profile for personalized interactions
    user_profile = None
    try:
        supabase = get_supabase_client()
        profile_result = await asyncio.to_thread(
            lambda: supabase.table("user_profiles")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        if profile_result.data:
            user_profile = profile_result.data[0]
    except Exception as e:
        logger.warning(f"Warning: Could not load user profile: {e}")

    full_prompt = build_system_prompt(user_profile)

    # Initialize conversation memory
    messages = {
        "messages": [
            {
                "role": "system",
                "content": full_prompt,
            }
        ],
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

            if len(user_input) > MAX_MESSAGE_LENGTH:
                await websocket.send_text(
                    f"Message too long ({len(user_input)} characters). Please keep it under {MAX_MESSAGE_LENGTH} characters."
                )
                continue

            if not limiter.limiter.hit(CHAT_RATE_LIMIT, user_id):
                await websocket.send_text("You are sending messages too fast. Please wait a moment.")
                continue

            async with _keepalive(websocket):
                await _process_user_message(
                    websocket,
                    user_input,
                    current_session_id,
                    user_id,
                    token,
                    messages,
                    model,
                    label_encoder,
                    chat_client,
                    chat_model,
                )

    except WebSocketDisconnect:
        # Clean up session on disconnect
        # Use the current_session_id we created for this connection
        if current_session_id in active_connections:
            del active_connections[current_session_id]
        # Don't call websocket.close() here - it's already closed and causes AttributeError
