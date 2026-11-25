from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

router = APIRouter()

_INDEX = Path(__file__).resolve().parents[2] / "static" / "index.html"


@router.get("/", include_in_schema=False)
async def index() -> Response:
    return HTMLResponse(_INDEX.read_text(encoding="utf-8"))
