from fastapi import APIRouter, Query

from app.schemas.analysis import CaseOptionsResponse
from app.services.sheets import SheetsClient

router = APIRouter()


@router.get("/options", response_model=CaseOptionsResponse)
async def list_case_options(
    limit: int = Query(default=500, ge=1, le=2000),
    project_name: str = "",
    employee: str = "",
    technology: str = "",
    grade: str = "",
    source: str = "",
    date: str = "",
    sheet: str = "",
) -> CaseOptionsResponse:
    return SheetsClient().list_case_options(
        limit=limit,
        filters={
            "project_name": project_name,
            "employee": employee,
            "technology": technology,
            "grade": grade,
            "source": source,
            "date": date,
            "sheet": sheet,
        },
    )
