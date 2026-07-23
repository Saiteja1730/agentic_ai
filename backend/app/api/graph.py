"""Graph visualization endpoint: exposes the LangGraph topology."""
from fastapi import APIRouter

from app.graph.builder import get_graph_description
from app.schemas.schemas import GraphResponse

router = APIRouter(tags=["graph"])


@router.get("/graph", response_model=GraphResponse)
async def graph_description() -> GraphResponse:
    description = get_graph_description()
    return GraphResponse(**description)
