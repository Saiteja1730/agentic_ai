"""Smart Query Router: classifies queries heuristically without using an LLM to conserve quota."""
import re

def classify_query(query: str, use_pdf_context: bool) -> str:
    """
    Classify a user query into one of four routes:
    - COMPLEX_RESEARCH
    - PDF_SIMPLE
    - WEB_SIMPLE
    - GENERAL_SIMPLE
    """
    query_lower = query.lower()
    
    pdf_keywords = [
        "this pdf", "uploaded pdf", "uploaded file", "attached file", "attached document", 
        "document", "resume", "cv", "page", "section", "chapter", "this resume", 
        "candidate", "profile", "education", "experience", "skills", "projects", "summarize"
    ]
    
    web_keywords = ["latest", "current", "today", "news", "internet", "search", "recent", "this week"]
    
    general_keywords = ["what is", "what are", "how do", "how does", "explain", "tell me about"]
    complex_keywords = ["compare", "vs", "versus", "differences"]
    
    # Heuristics
    is_complex = any(kw in query_lower.split() for kw in complex_keywords) or query_lower.startswith("compare")
    has_web = any(kw in query_lower for kw in web_keywords)
    has_pdf = any(kw in query_lower for kw in pdf_keywords)
    
    def log_intent(intent: str, reason: str):
        print("\n[Router]")
        print(f"Intent:\n{intent}")
        print(f"Reason:\n{reason}\n{'-'*48}")
        return intent
    
    if is_complex and (has_web or has_pdf or use_pdf_context):
        return log_intent("COMPLEX_RESEARCH", "Requires uploaded document and external knowledge.")
        
    if has_pdf:
        return log_intent("PDF_SIMPLE", "Question explicitly references uploaded document.")
        
    if has_web:
        return log_intent("WEB_SIMPLE", "Current or live information requested.")
        
    if any(query_lower.startswith(kw) or f" {kw} " in query_lower for kw in general_keywords):
        return log_intent("GENERAL_SIMPLE", "General knowledge query. No uploaded document required.")
        
    if use_pdf_context:
        return log_intent("PDF_SIMPLE", "Context active: defaulting to PDF search.")
        
    return log_intent("GENERAL_SIMPLE", "Fallback: General knowledge query.")
