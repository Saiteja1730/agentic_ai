"""Tool registry for managing LLM-callable functions."""
import inspect
from typing import Any, Callable, Dict, List

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """A modular registry for LLM tools."""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        
    def register(self, func: Callable) -> Callable:
        """Register a tool function."""
        name = func.__name__
        self._tools[name] = func
        logger.debug("Registered tool: %s", name)
        return func
        
    def get_tool(self, name: str) -> Callable | None:
        """Retrieve a tool by name."""
        return self._tools.get(name)
        
    def get_all_tools(self) -> List[Callable]:
        """Get all registered tool functions (used to pass to the SDK)."""
        return list(self._tools.values())
        
    async def execute_tool(self, name: str, kwargs: dict) -> Any:
        """Execute a tool dynamically."""
        func = self.get_tool(name)
        if not func:
            raise ValueError(f"Tool not found: {name}")
            
        logger.info("Executing tool %s with args %s", name, kwargs)
        
        if inspect.iscoroutinefunction(func):
            import asyncio
            try:
                # Wrap tool execution in a hard timeout so it doesn't block Gemini indefinitely
                return await asyncio.wait_for(func(**kwargs), timeout=15.0)
            except asyncio.TimeoutError:
                logger.error("Tool %s timed out after 15 seconds.", name)
                raise TimeoutError(f"Tool {name} timed out.")
        return func(**kwargs)


# Global default registry
registry = ToolRegistry()
