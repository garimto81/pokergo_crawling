"""Category and CategoryEntry API endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..database.models import Category, CategoryEntry, NasFile
from ..schemas.category import (
    CategoryEntryBatchVerifyRequest,
    CategoryEntryDetailResponse,
    CategoryEntryListResponse,
    CategoryEntryResponse,
    CategoryEntryUpdate,
    CategoryEntryVerifyRequest,
    CategoryListResponse,
    CategoryResponse,
    EntryFileInfo,
    KPIStats,
    MatchTypeStats,
    SourceStats,
    TitleGenerationResult,
)
from ..services.title_generation import (
    generate_titles_for_none_entries,
    improve_all_titles,
)

router = APIRouter(prefix="/api", tags=["categories"])


# =============================================================================
# Category Endpoints
# =============================================================================

@router.get("/categories", response_model=CategoryListResponse)
def get_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    year: Optional[int] = None,
    region: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """카테고리 목록 조회."""
    query = db.query(Category)

    # Filters
    if year:
        query = query.filter(Category.year == year)
    if region:
        query = query.filter(Category.region == region)
    if source:
        query = query.filter(Category.source == source)

    # Count
    total = query.count()

    # Paginate
    categories = query.order_by(Category.year.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # Add entry counts
    items = []
    for cat in categories:
        entry_count = db.query(CategoryEntry).filter(
            CategoryEntry.category_id == cat.id
        ).count()

        file_count = db.query(NasFile).join(CategoryEntry).filter(
            CategoryEntry.category_id == cat.id
        ).count()

        total_size = db.query(func.sum(NasFile.size_bytes)).join(CategoryEntry).filter(
            CategoryEntry.category_id == cat.id
        ).scalar() or 0

        items.append(CategoryResponse(
            id=cat.id,
            code=cat.code,
            name=cat.name,
            year=cat.year,
            region=cat.region,
            source=cat.source,
            pokergo_category=cat.pokergo_category,
            description=cat.description,
            entry_count=entry_count,
            file_count=file_count,
            total_size_gb=total_size / (1024 ** 3),
            created_at=cat.created_at,
        ))

    return CategoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """카테고리 상세 조회."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    entry_count = db.query(CategoryEntry).filter(
        CategoryEntry.category_id == category_id
    ).count()

    return CategoryResponse(
        id=category.id,
        code=category.code,
        name=category.name,
        year=category.year,
        region=category.region,
        source=category.source,
        pokergo_category=category.pokergo_category,
        description=category.description,
        entry_count=entry_count,
        created_at=category.created_at,
    )


@router.get("/categories/{category_id}/entries", response_model=CategoryEntryListResponse)
def get_category_entries(
    category_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """특정 카테고리의 Entry 목록."""
    query = db.query(CategoryEntry).filter(CategoryEntry.category_id == category_id)

    total = query.count()
    entries = query.order_by(CategoryEntry.sequence).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return CategoryEntryListResponse(
        items=[CategoryEntryResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Entry Endpoints
# =============================================================================

@router.get("/entries", response_model=CategoryEntryListResponse)
def get_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    match_type: Optional[str] = None,
    source: Optional[str] = None,
    verified: Optional[bool] = None,
    year: Optional[int] = None,
    event_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Entry 목록 조회."""
    query = db.query(CategoryEntry)

    # Filters
    if match_type:
        query = query.filter(CategoryEntry.match_type == match_type)
    if source:
        query = query.filter(CategoryEntry.source == source)
    if verified is not None:
        query = query.filter(CategoryEntry.verified == verified)
    if year:
        query = query.filter(CategoryEntry.year == year)
    if event_type:
        query = query.filter(CategoryEntry.event_type == event_type)
    if search:
        query = query.filter(CategoryEntry.display_title.ilike(f'%{search}%'))

    total = query.count()
    entries = query.order_by(
        CategoryEntry.year.desc(),
        CategoryEntry.sequence
    ).offset((page - 1) * page_size).limit(page_size).all()

    return CategoryEntryListResponse(
        items=[CategoryEntryResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/entries/{entry_id}", response_model=CategoryEntryDetailResponse)
def get_entry(entry_id: int, db: Session = Depends(get_db)):
    """Entry 상세 조회 (파일 포함)."""
    entry = db.query(CategoryEntry).filter(CategoryEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Get category name
    category = db.query(Category).filter(Category.id == entry.category_id).first()
    category_name = category.name if category else None

    # Get files
    files = db.query(NasFile).filter(NasFile.entry_id == entry_id).all()

    return CategoryEntryDetailResponse(
        **CategoryEntryResponse.model_validate(entry).model_dump(),
        category_name=category_name,
        files=[EntryFileInfo.model_validate(f) for f in files],
    )


@router.patch("/entries/{entry_id}", response_model=CategoryEntryResponse)
def update_entry(
    entry_id: int,
    data: CategoryEntryUpdate,
    db: Session = Depends(get_db),
):
    """Entry 수정."""
    entry = db.query(CategoryEntry).filter(CategoryEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)

    return CategoryEntryResponse.model_validate(entry)


@router.post("/entries/{entry_id}/verify", response_model=CategoryEntryResponse)
def verify_entry(
    entry_id: int,
    data: CategoryEntryVerifyRequest,
    db: Session = Depends(get_db),
):
    """Entry 검증 완료 처리."""
    entry = db.query(CategoryEntry).filter(CategoryEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry.verified = True
    entry.verified_at = datetime.utcnow()
    entry.verified_by = data.verified_by
    if data.notes:
        entry.notes = data.notes
    entry.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(entry)

    return CategoryEntryResponse.model_validate(entry)


@router.post("/entries/verify-batch")
def verify_entries_batch(
    data: CategoryEntryBatchVerifyRequest,
    db: Session = Depends(get_db),
):
    """여러 Entry 일괄 검증."""
    verified_count = 0
    now = datetime.utcnow()

    for entry_id in data.entry_ids:
        entry = db.query(CategoryEntry).filter(CategoryEntry.id == entry_id).first()
        if entry and not entry.verified:
            entry.verified = True
            entry.verified_at = now
            entry.verified_by = data.verified_by
            entry.updated_at = now
            verified_count += 1

    db.commit()

    return {"verified_count": verified_count, "total_requested": len(data.entry_ids)}


# =============================================================================
# Title Generation Endpoints
# =============================================================================

@router.post("/entries/generate-titles", response_model=TitleGenerationResult)
def generate_titles(
    use_ai: bool = Query(False),
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
):
    """NONE 항목의 제목 생성."""
    result = generate_titles_for_none_entries(db, use_ai=use_ai, dry_run=dry_run)
    return TitleGenerationResult(**result)


@router.post("/entries/improve-titles", response_model=TitleGenerationResult)
def improve_titles(
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
):
    """모든 제목의 일관성 개선."""
    result = improve_all_titles(db, dry_run=dry_run)
    return TitleGenerationResult(
        total=result['total'],
        improved=result['improved'],
        samples=result['samples'],
    )


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/stats/kpi", response_model=KPIStats)
def get_kpi_stats(db: Session = Depends(get_db)):
    """KPI 통계 조회."""
    total_entries = db.query(CategoryEntry).count()
    total_files = db.query(NasFile).count()
    active_files = db.query(NasFile).filter(NasFile.is_excluded == False).count()

    # Files with entry_id
    files_with_entry = db.query(NasFile).filter(
        NasFile.entry_id.isnot(None)
    ).count()

    # Entries with display_title
    entries_with_title = db.query(CategoryEntry).filter(
        CategoryEntry.display_title.isnot(None)
    ).count()

    # Source distribution
    pokergo_count = db.query(CategoryEntry).filter(
        CategoryEntry.source == 'POKERGO'
    ).count()
    nas_only_count = db.query(CategoryEntry).filter(
        CategoryEntry.source == 'NAS_ONLY'
    ).count()

    # Verified count
    verified_count = db.query(CategoryEntry).filter(
        CategoryEntry.verified == True
    ).count()

    # Match type distribution
    exact = db.query(CategoryEntry).filter(CategoryEntry.match_type == 'EXACT').count()
    partial = db.query(CategoryEntry).filter(CategoryEntry.match_type == 'PARTIAL').count()
    manual = db.query(CategoryEntry).filter(CategoryEntry.match_type == 'MANUAL').count()
    none = db.query(CategoryEntry).filter(CategoryEntry.match_type == 'NONE').count()

    # Verification needed (PARTIAL & not verified)
    verification_needed = db.query(CategoryEntry).filter(
        CategoryEntry.match_type == 'PARTIAL',
        CategoryEntry.verified == False,
    ).count()

    # Calculate KPIs
    category_coverage = (files_with_entry / active_files * 100) if active_files > 0 else 0
    title_completeness = (entries_with_title / total_entries * 100) if total_entries > 0 else 0
    pokergo_utilization = (pokergo_count / total_entries * 100) if total_entries > 0 else 0
    verification_rate = (verified_count / total_entries * 100) if total_entries > 0 else 0

    return KPIStats(
        total_entries=total_entries,
        total_files=total_files,
        active_files=active_files,
        category_coverage=round(category_coverage, 1),
        title_completeness=round(title_completeness, 1),
        pokergo_utilization=round(pokergo_utilization, 1),
        verification_rate=round(verification_rate, 1),
        match_type_stats=MatchTypeStats(
            exact=exact,
            partial=partial,
            manual=manual,
            none=none,
        ),
        source_stats=SourceStats(
            pokergo=pokergo_count,
            nas_only=nas_only_count,
        ),
        verification_needed=verification_needed,
    )


# =============================================================================
# Content Explorer Tree Endpoint
# =============================================================================

@router.get("/content-tree")
def get_content_tree(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Content Explorer 트리 데이터 조회.
    
    Year → Category → EventType → Entry 계층 구조.
    """
    from collections import defaultdict
    
    # Get all entries with category info
    query = db.query(CategoryEntry).join(Category)
    if year:
        query = query.filter(CategoryEntry.year == year)
    
    entries = query.order_by(
        CategoryEntry.year.desc(),
        CategoryEntry.entry_code
    ).all()
    
    # Build hierarchical structure
    year_map = defaultdict(lambda: {
        'entry_count': 0,
        'exact_count': 0,
        'none_count': 0,
        'pokergo_only_count': 0,
        'total_size': 0,
        'categories': defaultdict(lambda: {
            'name': '',
            'region': '',
            'entry_count': 0,
            'exact_count': 0,
            'none_count': 0,
            'pokergo_only_count': 0,
            'event_types': defaultdict(lambda: {
                'name': '',
                'entry_count': 0,
                'exact_count': 0,
                'none_count': 0,
                'pokergo_only_count': 0,
                'entries': []
            })
        })
    })
    
    # Event type names mapping
    event_type_names = {
        'ME': 'Main Event',
        'BR': 'Bracelet Events',
        'HR': 'High Roller',
        'HU': 'Heads Up',
        'GM': 'Grudge Match',
        'EU': 'Europe',
        'APAC': 'Asia Pacific',
        'PAD': 'Paradise',
    }
    
    # Process entries
    for entry in entries:
        y = entry.year
        cat = entry.category
        et = entry.event_type or 'OTHER'
        
        # Year level
        year_map[y]['entry_count'] += 1
        year_map[y]['total_size'] += entry.total_size_bytes or 0
        if entry.match_type == 'EXACT':
            year_map[y]['exact_count'] += 1
        elif entry.match_type == 'NONE':
            year_map[y]['none_count'] += 1
        elif entry.match_type == 'POKERGO_ONLY':
            year_map[y]['pokergo_only_count'] += 1

        # Category level
        if cat:
            cat_key = cat.code
            year_map[y]['categories'][cat_key]['name'] = cat.name
            year_map[y]['categories'][cat_key]['region'] = cat.region
            year_map[y]['categories'][cat_key]['id'] = cat.id
            year_map[y]['categories'][cat_key]['entry_count'] += 1
            if entry.match_type == 'EXACT':
                year_map[y]['categories'][cat_key]['exact_count'] += 1
            elif entry.match_type == 'NONE':
                year_map[y]['categories'][cat_key]['none_count'] += 1
            elif entry.match_type == 'POKERGO_ONLY':
                year_map[y]['categories'][cat_key]['pokergo_only_count'] += 1

            # Event type level
            year_map[y]['categories'][cat_key]['event_types'][et]['name'] = event_type_names.get(et, et)
            year_map[y]['categories'][cat_key]['event_types'][et]['entry_count'] += 1
            if entry.match_type == 'EXACT':
                year_map[y]['categories'][cat_key]['event_types'][et]['exact_count'] += 1
            elif entry.match_type == 'NONE':
                year_map[y]['categories'][cat_key]['event_types'][et]['none_count'] += 1
            elif entry.match_type == 'POKERGO_ONLY':
                year_map[y]['categories'][cat_key]['event_types'][et]['pokergo_only_count'] += 1
            
            # Entry level
            year_map[y]['categories'][cat_key]['event_types'][et]['entries'].append({
                'id': entry.id,
                'entry_code': entry.entry_code,
                'display_title': entry.display_title,
                'pokergo_title': entry.pokergo_title,
                'match_type': entry.match_type,
                'match_score': entry.match_score,
                'file_count': entry.file_count or 0,
                'total_size_gb': round((entry.total_size_bytes or 0) / (1024**3), 2),
            })
    
    # Convert to response format
    years = []
    for y in sorted(year_map.keys(), reverse=True):
        y_data = year_map[y]
        categories = []
        for cat_code, cat_data in y_data['categories'].items():
            event_types = []
            for et_code, et_data in cat_data['event_types'].items():
                event_types.append({
                    'code': et_code,
                    'name': et_data['name'],
                    'entry_count': et_data['entry_count'],
                    'exact_count': et_data['exact_count'],
                    'none_count': et_data['none_count'],
                    'pokergo_only_count': et_data['pokergo_only_count'],
                    'entries': et_data['entries'],
                })
            categories.append({
                'id': cat_data.get('id', 0),
                'code': cat_code,
                'name': cat_data['name'],
                'region': cat_data['region'],
                'entry_count': cat_data['entry_count'],
                'exact_count': cat_data['exact_count'],
                'none_count': cat_data['none_count'],
                'pokergo_only_count': cat_data['pokergo_only_count'],
                'event_types': sorted(event_types, key=lambda x: -x['entry_count']),
            })
        years.append({
            'year': y,
            'entry_count': y_data['entry_count'],
            'exact_count': y_data['exact_count'],
            'none_count': y_data['none_count'],
            'pokergo_only_count': y_data['pokergo_only_count'],
            'total_size_gb': round(y_data['total_size'] / (1024**3), 2),
            'categories': sorted(categories, key=lambda x: -x['entry_count']),
        })
    
    # Summary
    total_entries = sum(y['entry_count'] for y in years)
    total_exact = sum(y['exact_count'] for y in years)
    total_none = sum(y['none_count'] for y in years)
    total_pokergo_only = sum(y['pokergo_only_count'] for y in years)
    total_size = sum(y['total_size_gb'] for y in years)

    return {
        'years': years,
        'summary': {
            'total_entries': total_entries,
            'exact_count': total_exact,
            'none_count': total_none,
            'pokergo_only_count': total_pokergo_only,
            'exact_rate': round(total_exact / total_entries * 100, 1) if total_entries > 0 else 0,
            'total_size_gb': round(total_size, 2),
            'year_count': len(years),
        }
    }
