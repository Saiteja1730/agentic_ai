"""Utility tools for LLM agents."""
import ast
import operator
from datetime import datetime
from typing import Any

from app.tools.registry import registry
from langsmith import traceable

# Allowed math operators for safe evaluation
_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _eval_expr(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.n
    elif isinstance(node, ast.BinOp):
        return _ALLOWED_OPS[type(node.op)](_eval_expr(node.left), _eval_expr(node.right))
    elif isinstance(node, ast.UnaryOp):
        return _ALLOWED_OPS[type(node.op)](_eval_expr(node.operand))
    else:
        raise TypeError(f"Unsupported syntax: {type(node)}")


@traceable(run_type="tool")
@registry.register
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.
    
    Args:
        expression: A mathematical expression string, e.g., '2 + 2 * 3'
    """
    try:
        # Safe evaluation of basic math expressions using AST
        node = ast.parse(expression, mode='eval').body
        result = _eval_expr(node)
        return str(result)
    except Exception as exc:
        return f"Error evaluating expression: {exc}"


@traceable(run_type="tool")
@registry.register
def current_date() -> str:
    """Get the current date and time in the format YYYY-MM-DD HH:MM:SS."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
