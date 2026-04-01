from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(include_in_schema=False)

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/report")
async def report_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "report.html")


@router.get("/analytics")
async def analytics_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "analytics.html")
