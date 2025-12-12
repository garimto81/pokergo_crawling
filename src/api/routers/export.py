"""
Export API Router
"""

import csv
import io
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse

from ..services import database

router = APIRouter()


@router.get("/report")
async def export_report(format: str = "json", status: Optional[str] = None):
    """전체 보고서 내보내기"""
    matches = database.get_all_matches_for_export(status)

    if format == "csv":
        output = io.StringIO()
        if matches:
            writer = csv.DictWriter(output, fieldnames=matches[0].keys())
            writer.writeheader()
            writer.writerows(matches)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=matching_report.csv"}
        )

    return JSONResponse(content={"total": len(matches), "matches": matches})


@router.get("/not-uploaded")
async def export_not_uploaded(format: str = "json"):
    """미업로드 목록 내보내기"""
    matches = database.get_all_matches_for_export(status="NOT_UPLOADED")

    # 점수 40 미만도 포함
    all_matches = database.get_all_matches_for_export()
    low_score = [m for m in all_matches if m.get("match_score", 0) < 40]

    # 중복 제거
    seen_ids = {m["id"] for m in matches}
    for m in low_score:
        if m["id"] not in seen_ids:
            matches.append(m)

    if format == "csv":
        output = io.StringIO()
        if matches:
            writer = csv.DictWriter(output, fieldnames=matches[0].keys())
            writer.writeheader()
            writer.writerows(matches)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=not_uploaded.csv"}
        )

    return JSONResponse(content={"total": len(matches), "matches": matches})
