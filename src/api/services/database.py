"""
Database service for content_mapping table
"""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

# 데이터베이스 경로
DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "db" / "pokergo.db"


@contextmanager
def get_connection():
    """SQLite 연결 컨텍스트 매니저"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_stats_summary() -> dict:
    """대시보드 통계 조회"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 전체 개수 및 상태별 개수
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN match_status = 'MATCHED' THEN 1 ELSE 0 END) as matched,
                SUM(CASE WHEN match_status = 'LIKELY' THEN 1 ELSE 0 END) as likely,
                SUM(CASE WHEN match_status = 'POSSIBLE' THEN 1 ELSE 0 END) as possible,
                SUM(CASE WHEN match_status = 'NOT_UPLOADED' THEN 1 ELSE 0 END) as not_uploaded,
                SUM(CASE WHEN match_status = 'VERIFIED' THEN 1 ELSE 0 END) as verified,
                SUM(CASE WHEN match_status = 'MANUAL_MATCH' THEN 1 ELSE 0 END) as manual_match,
                AVG(match_score) as avg_score
            FROM content_mapping
        """)
        row = cursor.fetchone()

        total = row["total"] or 0
        matched = row["matched"] or 0
        likely = row["likely"] or 0

        match_rate = ((matched + likely) / total * 100) if total > 0 else 0

        return {
            "total": total,
            "by_status": {
                "MATCHED": row["matched"] or 0,
                "LIKELY": row["likely"] or 0,
                "POSSIBLE": row["possible"] or 0,
                "NOT_UPLOADED": row["not_uploaded"] or 0,
                "VERIFIED": row["verified"] or 0,
                "MANUAL_MATCH": row["manual_match"] or 0
            },
            "match_rate": round(match_rate, 1),
            "avg_score": round(row["avg_score"] or 0, 1)
        }


def get_not_uploaded_categories() -> dict:
    """미업로드 콘텐츠 카테고리별 분류"""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                nas_directory,
                COUNT(*) as count,
                GROUP_CONCAT(nas_filename, '|||') as filenames,
                GROUP_CONCAT(match_score, '|||') as scores
            FROM content_mapping
            WHERE match_status = 'NOT_UPLOADED' OR match_score < 40
            GROUP BY nas_directory
            ORDER BY count DESC
        """)

        categories = []
        total = 0

        for row in cursor.fetchall():
            filenames = row["filenames"].split("|||") if row["filenames"] else []
            scores = row["scores"].split("|||") if row["scores"] else []

            files = [
                {"filename": f, "score": int(s) if s else 0}
                for f, s in zip(filenames, scores)
            ]

            categories.append({
                "directory": row["nas_directory"] or "Unknown",
                "count": row["count"],
                "files": files[:5]  # 최대 5개만
            })
            total += row["count"]

        return {
            "total": total,
            "categories": categories
        }


def get_score_distribution(bins: int = 10) -> dict:
    """점수 분포 히스토그램"""
    with get_connection() as conn:
        cursor = conn.cursor()

        bin_size = 100 // bins
        bin_edges = list(range(0, 101, bin_size))
        counts = [0] * bins

        cursor.execute("SELECT match_score FROM content_mapping")

        for row in cursor.fetchall():
            score = row["match_score"] or 0
            bin_idx = min(score // bin_size, bins - 1)
            counts[bin_idx] += 1

        return {
            "bins": bin_edges[:-1],
            "counts": counts
        }


def get_matches(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    score_min: Optional[int] = None,
    score_max: Optional[int] = None,
    year: Optional[str] = None,
    event: Optional[str] = None,
    search: Optional[str] = None
) -> dict:
    """매칭 목록 조회"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # WHERE 절 구성
        conditions = []
        params = []

        if status:
            conditions.append("match_status = ?")
            params.append(status)

        if score_min is not None:
            conditions.append("match_score >= ?")
            params.append(score_min)

        if score_max is not None:
            conditions.append("match_score <= ?")
            params.append(score_max)

        if search:
            conditions.append("(nas_filename LIKE ? OR youtube_title LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # 전체 개수
        cursor.execute(f"SELECT COUNT(*) as total FROM content_mapping{where_clause}", params)
        total = cursor.fetchone()["total"]

        # 페이지네이션
        offset = (page - 1) * limit
        pages = (total + limit - 1) // limit

        cursor.execute(f"""
            SELECT * FROM content_mapping
            {where_clause}
            ORDER BY match_score DESC, id ASC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])

        items = [dict(row) for row in cursor.fetchall()]

        return {
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit
        }


def get_match_by_id(match_id: int) -> Optional[dict]:
    """단일 매칭 조회"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM content_mapping WHERE id = ?", (match_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_match(match_id: int, updates: dict) -> Optional[dict]:
    """매칭 업데이트"""
    with get_connection() as conn:
        cursor = conn.cursor()

        set_parts = []
        params = []

        for key, value in updates.items():
            if value is not None:
                set_parts.append(f"{key} = ?")
                params.append(value)

        if not set_parts:
            return get_match_by_id(match_id)

        set_parts.append("updated_at = CURRENT_TIMESTAMP")
        params.append(match_id)

        cursor.execute(f"""
            UPDATE content_mapping
            SET {', '.join(set_parts)}
            WHERE id = ?
        """, params)

        conn.commit()
        return get_match_by_id(match_id)


def bulk_update_matches(ids: list[int], status: str, notes: Optional[str] = None) -> int:
    """일괄 업데이트"""
    with get_connection() as conn:
        cursor = conn.cursor()

        placeholders = ",".join("?" * len(ids))

        cursor.execute(f"""
            UPDATE content_mapping
            SET match_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        """, [status] + ids)

        conn.commit()
        return cursor.rowcount


def get_all_matches_for_export(status: Optional[str] = None) -> list[dict]:
    """내보내기용 전체 매칭 조회"""
    with get_connection() as conn:
        cursor = conn.cursor()

        if status:
            cursor.execute(
                "SELECT * FROM content_mapping WHERE match_status = ? ORDER BY id",
                (status,)
            )
        else:
            cursor.execute("SELECT * FROM content_mapping ORDER BY id")

        return [dict(row) for row in cursor.fetchall()]
