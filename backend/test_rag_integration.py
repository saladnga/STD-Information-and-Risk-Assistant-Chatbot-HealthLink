#!/usr/bin/env python3
"""
Test script to verify RAG integration works correctly.
"""

import sys
import os

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.rag.retriever import retrieve_and_answer
    print("✅ Successfully imported retrieve_and_answer")
    
    # Test retrieval
    print("\n🔍 Testing RAG retrieval...")
    test_query = "What are the symptoms of chlamydia?"
    
    answer, sources, confidence, citations = retrieve_and_answer(
        question=test_query,
        max_results=3
    )
    
    print(f"📊 Query: {test_query}")
    print(f"📝 Answer: {answer[:200]}...")
    print(f"🎯 Confidence: {confidence}")
    print(f"📚 Number of sources: {len(sources) if sources else 0}")
    
    if sources:
        print("📖 Sources:")
        for i, source in enumerate(sources[:2], 1):
            print(f"   {i}. {source.get('filename', 'Unknown')} (Page {source.get('page', 'N/A')})")
    
    if citations:
        print(f"📄 Citations: {len(citations)} found")
        
    print("\n✅ RAG integration test completed successfully!")
    
except Exception as e:
    print(f"❌ Error testing RAG integration: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()