from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.api.auth import TokenData, ensure_org_access, get_current_user, require_admin, resolve_org_scope
from app.db.engine import db_session
from app.repositories.user_repo import UserRepository
from app.models.user import User
from app.services.pal_score_service import PALScoreService

pal_router = APIRouter(prefix="/pal", tags=["PAL"])

# Mock ATS Stats Config
ATS_STATS_CONFIG = {
    "pal_distribution": [
        {"range": "90-100%", "count": 2, "width": 40, "color": "emerald"},
        {"range": "75-89%", "count": 1, "width": 20, "color": "brand"},
        {"range": "60-74%", "count": 1, "width": 20, "color": "amber"},
        {"range": "45-59%", "count": 1, "width": 20, "color": "amber"},
        {"range": "Below 45%", "count": 0, "width": 0, "color": "red"},
    ]
}

def _list_pal_leaderboard(db: Session, category_slug: str, org_id: int | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    stmt = select(User).where(
        User.role == "learner",
        User.is_active == True,
        User.category_scope == category_slug
    )
    if org_id is not None:
        stmt = stmt.where(User.org_id == org_id)
        
    stmt = stmt.order_by(desc(User.pal_score), User.full_name)
    if limit is not None:
        stmt = stmt.limit(limit)
        
    users = db.execute(stmt).scalars().all()
    if org_id is not None:
        service = PALScoreService(db)
        for user in users:
            service.recompute_user(user.id, org_id)
        users.sort(key=lambda user: (-(user.pal_score or 0), user.full_name or ""))
    return [u.to_dict() for u in users]

@pal_router.get("/leaderboard/{category_slug}")
def get_leaderboard(
    category_slug: str,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    if current_user.role == "category_admin" and current_user.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="You do not have access to this category.")
    scoped_org_id = resolve_org_scope(current_user, org_id)
    return {"leaderboard": _list_pal_leaderboard(db, category_slug, org_id=scoped_org_id)}

@pal_router.get("/users/{user_id}")
def get_pal_user(
    user_id: str, 
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session)
):
    if current_user.role == "learner" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own PAL detail.")
        
    user_repo = UserRepository(db)
    target = user_repo.get_by_id(user_id)
    
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
        
    ensure_org_access(current_user, target.org_id)
    
    metrics = PALScoreService(db).recompute_user(target.id, target.org_id)
    rank = PALScoreService(db).rank_for_user(target.id, target.category_scope, target.org_id)
    return {
        "user": target.to_dict(),
        "metrics": {
            "completion_pct": metrics["course_completion"],
            "quiz_avg": metrics["quiz_average"],
            "assignment_average": metrics["assignment_average"],
            "time_spent_hours": getattr(target, 'pal_time_spent_hours', 0) or 0,
            "task_completion_pct": metrics["task_completion"],
            "streak_days": getattr(target, 'streak_days', 0) or 0,
            "pal_score": metrics["pal_score"],
            "current_rank": rank,
            "progress_trend": metrics["progress_trend"],
            "strengths": metrics["strengths"],
            "weak_areas": metrics["weak_areas"],
            "completion_timeline": metrics["completion_timeline"],
        },
        "course_progress": getattr(target, 'course_progress', []),
    }

@pal_router.get("/distribution/{category_slug}")
def get_distribution(
    category_slug: str,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    if current_user.role == "category_admin" and current_user.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="You do not have access to this category.")
        
    scoped_org_id = resolve_org_scope(current_user, org_id)
    
    if category_slug == "ats":
        return {"distribution": ATS_STATS_CONFIG["pal_distribution"]}
        
    leaderboard = _list_pal_leaderboard(db, category_slug, org_id=scoped_org_id)
    buckets = [
        ("90-100%", 90, 100, "emerald"),
        ("75-89%", 75, 89, "brand"),
        ("60-74%", 60, 74, "amber"),
        ("45-59%", 45, 59, "amber"),
        ("Below 45%", 0, 44, "red"),
    ]
    result = []
    total = max(len(leaderboard), 1)
    for label, low, high, color in buckets:
        count = sum(1 for learner in leaderboard if low <= learner.get("pal_score", 0) <= high)
        result.append(
            {
                "range": label,
                "count": count,
                "width": round((count / total) * 100),
                "color": color,
            }
        )
    return {"distribution": result}

@pal_router.post("/compute")
def post_compute(
    category_slug: str | None = None,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    if current_user.role == "category_admin":
        category_slug = current_user.category_scope
        
    service = PALScoreService(db)
    if category_slug:
        rows = service.recompute_category(category_slug, scoped_org_id)
    else:
        users = db.execute(select(User).where(User.role == "learner", User.org_id == scoped_org_id)).scalars().all()
        rows = [service.recompute_user(user.id, scoped_org_id) for user in users]
    db.commit()
    return {"status": "success", "message": "PAL recomputed successfully", "updated": len(rows)}
