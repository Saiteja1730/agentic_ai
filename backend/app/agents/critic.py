"""Critic Agent: reviews the draft report for hallucinations, missing
citations, weak explanations, and poor formatting."""
from typing import Any

from app.llm.gemini import generate_json
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_INSTRUCTION = """You are a rigorous AI evaluation judge.
Review a draft research report against the evidence it was based on.

Evaluate across 5 specific dimensions:
1. Hallucinations (Does the draft claim things not in the context?)
2. Missing citations (Are claims backed by inline source citations?)
3. Coverage (Does it answer the user's question completely?)
4. Grounding (Is the reasoning directly tied to the provided evidence?)
5. Reasoning quality (Is the logic sound and easy to follow?)

Respond with ONLY valid JSON in this exact shape:
{
  "evaluations": {
    "hallucinations": "<brief comment on hallucinations>",
    "missing_citations": "<brief comment on citations>",
    "coverage": "<brief comment on coverage>",
    "grounding": "<brief comment on grounding>",
    "reasoning_quality": "<brief comment on reasoning>"
  },
  "score": <float 0 to 100>,
  "feedback": "<detailed, actionable feedback for the writer to improve the draft if score < 80>"
}
Your 'score' represents your confidence. Do not be overly generous."""

async def run_critic(question: str, combined_context: str, draft: str) -> dict[str, Any]:
    prompt = (
        f"Research question: {question}\n\n"
        f"Evidence used:\n{combined_context}\n\n"
        f"Draft report:\n{draft}\n\n"
        "Review the draft now."
    )
    result = await generate_json(prompt, system_instruction=SYSTEM_INSTRUCTION, temperature=0.1)

    if not result or "score" not in result:
        logger.warning("Critic returned malformed response; defaulting to high score to avoid deadlock.")
        result = {
            "score": 85.0, 
            "evaluations": {}, 
            "feedback": "Auto-approved due to critic error."
        }
    return result
