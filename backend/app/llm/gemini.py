"""Thin async wrapper around the Google GenAI SDK for Gemini 2.5 Flash."""
import json
from typing import Any, Optional

from google import genai
from google.genai import types

from app.config.settings import get_settings
from app.utils.logger import get_logger
from app.utils.retry import async_retry
from langsmith import traceable

settings = get_settings()
logger = get_logger(__name__)

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY is not set; Gemini calls will fail.")
        _client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    return _client


FALLBACK_MODELS = [settings.GEMINI_MODEL]


@traceable(run_type="llm")
@async_retry(max_attempts=3, base_delay=1.5)
async def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.4,
    max_output_tokens: int = 4096,
) -> str:
    """Generate free-form text from Gemini with automatic model fallback."""
    client = get_client()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    
    last_exc = None
    # Deduplicate fallback models while preserving order
    models_to_try = list(dict.fromkeys(FALLBACK_MODELS))
    
    for model_name in models_to_try:
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as exc:
            last_exc = exc
            logger.warning("Gemini call failed for model '%s': %s", model_name, exc)
            
    if last_exc:
        raise last_exc
    return ""


@traceable(run_type="llm")
@async_retry(max_attempts=3, base_delay=1.5)
async def generate_json(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Generate structured JSON output from Gemini, with defensive parsing."""
    client = get_client()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        response_mime_type="application/json",
    )
    
    last_exc = None
    models_to_try = list(dict.fromkeys(FALLBACK_MODELS))
    raw = ""
    
    for model_name in models_to_try:
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            raw = (response.text or "").strip()
            break
        except Exception as exc:
            last_exc = exc
            logger.warning("Gemini JSON call failed for model '%s': %s", model_name, exc)
            
    if not raw and last_exc:
        raise last_exc

    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from Gemini response: %s", raw[:500])
        return {}


def get_tool_declarations() -> list[types.Tool]:
    """Helper to declare tools explicitly to avoid SDK async/coroutine errors."""
    return [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="web_search",
                    description="Search the web for information using Tavily.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "query": types.Schema(
                                type="STRING", 
                                description="The search query string."
                            )
                        },
                        required=["query"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="pdf_search",
                    description="Search uploaded PDF documents for information.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "query": types.Schema(
                                type="STRING", 
                                description="The search query string."
                            ),
                            "session_id": types.Schema(
                                type="STRING", 
                                description="The current session ID (must be provided)."
                            ),
                        },
                        required=["query", "session_id"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="calculator",
                    description="Evaluate a mathematical expression and return the result.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "expression": types.Schema(
                                type="STRING", 
                                description="A mathematical expression string, e.g., '2 + 2 * 3'"
                            )
                        },
                        required=["expression"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="current_date",
                    description="Get the current date and time.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={},
                    ),
                ),
            ]
        )
    ]


@traceable(run_type="llm")
async def generate_with_tools(
    prompt: str,
    tools: list[Any],
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    require_json: bool = False,
    max_total_calls: int = 6,
    max_same_calls: int = 2,
) -> str:
    """Generate text using Gemini, dynamically executing provided tools in a loop."""
    client = get_client()
    
    # Use explicit schemas to prevent the SDK from inspecting and rejecting coroutines
    declarations = get_tool_declarations()
    
    kwargs = {
        "system_instruction": system_instruction,
        "temperature": temperature,
        "tools": declarations,
        "automatic_function_calling": {"disable": True},
        "thinking_config": types.ThinkingConfig(thinking_budget=0),
    }
    if require_json:
        kwargs["response_mime_type"] = "application/json"
        
    config = types.GenerateContentConfig(**kwargs)
    
    # Use a Chat session to maintain history automatically
    chat = client.aio.chats.create(model=settings.GEMINI_MODEL, config=config)
    
    logger.info("Sending message to model with %s tools...", len(declarations))
    response = await chat.send_message(prompt)
    
    from app.tools.registry import registry
    import string
    
    # Tool execution constraints
    MAX_TOTAL_TOOL_CALLS = max_total_calls
    MAX_SAME_TOOL_CALLS = max_same_calls
    MAX_SAME_QUERY = 1
    
    total_calls = 0
    tool_counts = {}
    query_history = set()
    
    def normalize_query(q: str) -> str:
        if not isinstance(q, str):
            return str(q)
        q = q.lower()
        for p in string.punctuation:
            q = q.replace(p, "")
        return " ".join(q.split())
    
    while response.function_calls:
        parts = []
        for call in response.function_calls:
            name = call.name
            args = call.args or {}
            
            # Check total limits
            if total_calls >= MAX_TOTAL_TOOL_CALLS:
                logger.warning("MAX_TOTAL_TOOL_CALLS (%s) reached.", MAX_TOTAL_TOOL_CALLS)
                parts.append(types.Part.from_function_response(
                    name=name, 
                    response={"result": "Tool limit reached. Stop searching and generate the final answer with existing information."}
                ))
                continue
                
            # Check same tool limits
            tool_counts[name] = tool_counts.get(name, 0) + 1
            if tool_counts[name] > MAX_SAME_TOOL_CALLS:
                logger.warning("Duplicate tool prevented: %s called %s times.", name, tool_counts[name])
                parts.append(types.Part.from_function_response(
                    name=name, 
                    response={"result": "You have used this tool too many times. Please use a different tool or answer directly."}
                ))
                continue
                
            # Check duplicate semantic search
            is_duplicate = False
            if name in ["web_search", "pdf_search"] and "query" in args:
                norm_q = normalize_query(args["query"])
                if norm_q in query_history:
                    logger.warning("Duplicate search prevented for query: '%s'", norm_q)
                    is_duplicate = True
                    parts.append(types.Part.from_function_response(
                        name=name, 
                        response={"result": "Duplicate search. This query was already searched. Use existing context."}
                    ))
                else:
                    query_history.add(norm_q)
                    
            if is_duplicate:
                continue

            total_calls += 1
            
            try:
                result = await registry.execute_tool(name, args)
                parts.append(types.Part.from_function_response(name=name, response={"result": result}))
                logger.info("Tool %s executed successfully. Total calls: %s", name, total_calls)
            except Exception as e:
                logger.error("Error executing tool %s: %s", name, e)
                parts.append(types.Part.from_function_response(name=name, response={"error": str(e)}))
                
        # Send the tool responses back to the model
        try:
            response = await chat.send_message(parts)
        except Exception as exc:
            if "429 RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc):
                logger.error("Quota Exceeded (429) during tool loop: %s", exc)
                raise RuntimeError(f"QuotaExhaustedError: Google API rate limit reached. {exc}") from exc
            raise
        
    return response.text or ""
