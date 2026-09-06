#!/usr/bin/env python3
"""
Sanity-check script for the diagnosis pathway: runs a symptom description through the exact same ML prediction + RAG-citation logic the chatbot uses (see get_rag_context_for_diagnosis in routers/chatbot.py), and prints out the prediction plus every source it would actually have available - so you can eyeball whether the prediction looks reasonable and every citation is real, without digging through live chat logs.

Requires a trained model (backend/app/model.joblib) and, for the RAG check, real Supabase/OpenAI credentials in backend/app/.env (same as the app itself).

Usage:
    cd backend
    python test_analysis_citations.py
    python test_analysis_citations.py "yellow discharge, painful urination, no odor"
"""

import sys
import os
import glob
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

import pandas as pd
from model import load_model, process_text_to_feature
from knowledge_base import STD_KNOWLEDGE
from rag.retriever import retrieve_and_answer

PDF_DIR = os.path.join(os.path.dirname(__file__), "app", "data", "pdf")
REAL_PDF_NAMES = {os.path.basename(p) for p in glob.glob(os.path.join(PDF_DIR, "*.pdf"))}


async def check_symptoms(symptom_text: str):
    model, label_encoder, feature_columns = load_model()
    if model is None:
        print("No trained model found - train one first (POST /train), then rerun this.")
        return

    # --- Same prediction logic as run_ml_prediction() in chatbot.py ---
    feature_dict = process_text_to_feature(symptom_text, feature_columns)
    feature_df = pd.DataFrame([feature_dict], columns=feature_columns)
    probs = model.predict_proba(feature_df)[0]
    class_probability = dict(zip(label_encoder.classes_, probs.tolist()))
    prediction_class_name = label_encoder.inverse_transform(model.predict(feature_df))[0]
    confidence = class_probability[prediction_class_name] * 100

    print(f"\nSymptom text: {symptom_text!r}")
    print(f"Extracted symptoms: {[k for k, v in feature_dict.items() if v]}")
    print(f"\nPredicted condition: {prediction_class_name} ({confidence:.1f}% confidence)")
    print("Top 3 predictions:")
    for name, p in sorted(class_probability.items(), key=lambda kv: -kv[1])[:3]:
        print(f"  - {name}: {p * 100:.1f}%")

    # --- Same RAG-retrieval logic as get_rag_context_for_diagnosis() in chatbot.py ---
    rag_query = (
        f"What is {prediction_class_name}? Symptoms, treatment, causes, and "
        f"medical information about {prediction_class_name}. User symptoms: {symptom_text}"
    )
    _, rag_sources, _, _ = await asyncio.to_thread(
        retrieve_and_answer, question=rag_query, max_results=5,
    )

    print(f"\nRAG chunks found: {len(rag_sources) if rag_sources else 0}")
    if rag_sources:
        print("Citation check (each must match a real uploaded PDF):")
        for source in rag_sources:
            name = source.get("source", source.get("filename", "Unknown"))
            is_real = name in REAL_PDF_NAMES
            print(f"  {'OK  ' if is_real else 'FAKE'} - {name}")
            if not is_real:
                print("        ^ not one of the uploaded PDFs - this would be a fabricated/mismatched citation")
    else:
        info = STD_KNOWLEDGE.get(prediction_class_name, {})
        print("No RAG chunks matched - the chatbot falls back to the built-in knowledge base:")
        print(f"  Description: {info.get('description', '(none)')}")
        print(f"  Symptoms: {info.get('symptoms', [])}")
        print(f"  Treatment: {info.get('treatment', '(none)')}")
        print(
            "\nIMPORTANT: there is no real source in this case. If the chatbot's actual "
            "reply names a specific outside source (e.g. 'Mayo Clinic'), that citation was "
            "invented by the model, not retrieved from anywhere - treat it as fake."
        )


if __name__ == "__main__":
    # Defaults to the exact symptoms from the real conversation that
    # surfaced the fabricated "Mayo Clinic" citation, so running this with
    # no arguments reproduces that scenario directly.
    text = " ".join(sys.argv[1:]) or (
        "yellow discharge, burning and pain during urination, no odor, "
        "symptoms for the last 3 days"
    )
    asyncio.run(check_symptoms(text))
