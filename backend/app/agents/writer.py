"""Writer Agent: generates a professional markdown research report from evidence."""
from app.llm.gemini import generate_text
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_INSTRUCTION = """You are a professional research report writer.
Write clear, well-structured markdown reports using ONLY the evidence provided.
Never fabricate facts, statistics, or sources that are not present in the evidence.
Do NOT use inline citations like [1] or [Source: X].
Do NOT append a "References" or "Sources" section at the bottom, as the UI will display them automatically.
If the evidence states that no additional documents were found or that a tool limit was reached, do not mention the tool limits or errors in your report. Simply write the best possible answer using whatever valid facts are available.
Structure the report with these markdown headings exactly:
## Summary
## Detailed Explanation
## Key Findings"""


def _build_prompt(
    question: str,
    combined_context: str,
    critic_feedback: str | None = None,
    previous_draft: str | None = None,
    route: str = "GENERAL_SIMPLE",
) -> str:
    parts = [
        f"Research question: {question}",
        f"\nEvidence:\n{combined_context}",
    ]
    if previous_draft and critic_feedback:
        parts.append(
            f"\nA previous draft was reviewed and needs revision.\n"
            f"Previous draft:\n{previous_draft}\n\n"
            f"Critic feedback to address:\n{critic_feedback}\n"
            "Revise the report to fully address this feedback."
        )
        
    if route == "COMPLEX_RESEARCH":
        parts.append(
            "\n[CRITICAL REQUIREMENT]: Since this is a hybrid research task requiring comparison of uploaded documents against external web knowledge, YOU MUST structure the report exactly as follows:\n"
            "## Summary\n"
            "## Evidence from Uploaded Documents\n"
            "## Latest Web Information\n"
            "## Comparison\n"
            "## Conclusion\n"
        )
    else:
        parts.append("\nWrite the full markdown report now.")
        
    return "\n".join(parts)


async def run_writer(
    question: str,
    combined_context: str,
    critic_feedback: str | None = None,
    previous_draft: str | None = None,
    route: str = "GENERAL_SIMPLE",
) -> str:
    prompt = _build_prompt(question, combined_context, critic_feedback, previous_draft, route)
    draft = await generate_text(prompt, system_instruction=SYSTEM_INSTRUCTION, temperature=0.4, max_output_tokens=4096)
    return draft
