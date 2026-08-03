import csv
import json
from datetime import datetime
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.models.audit import AuditLog
from app.models.builder_activity_log import BuilderActivityLog
from app.models.course import Course
from app.models.user import User
from app.core.permissions import require_capability

audit_router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit Logs"])

def _generate_summary(log: AuditLog) -> str:
    action = log.action.lower()
    entity = (log.target_type or "record").replace("_", " ").title()
    
    # Format action to be human readable
    if action == "create":
        action_str = "Created"
    elif action == "update":
        action_str = "Updated"
    elif action == "delete":
        action_str = "Deleted"
    elif action == "course.published":
        return "Published Course"
    elif action == "course.submitted":
        return "Submitted Course for Review"
    elif action == "course.approved":
        return "Approved Course"
    elif action == "course.rejected":
        return "Rejected Course"
    elif action == "version.rollback":
        return "Rolled Back Version"
    elif action.startswith("media."):
        media_act = action.split(".")[1].capitalize()
        return f"{media_act} Media"
    else:
        action_str = action.capitalize()
        
    return f"{action_str} {entity}"

def _metadata(log: AuditLog) -> dict:
    if not log.metadata_json:
        return {}
    try:
        value = json.loads(log.metadata_json)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}

def _build_audit_query(db: Session, current_user: TokenData, course_id: str = None, action: str = None, user_id: str = None, entity_type: str = None, start_date: str = None, end_date: str = None):
    query = db.query(AuditLog).filter(
        AuditLog.org_id == current_user.org_id
    )

    if course_id:
        query = query.filter(AuditLog.metadata_json.ilike(f'%"course_id": "{course_id}"%'))
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        query = query.filter(AuditLog.actor_user_id == user_id)
    if entity_type:
        query = query.filter(AuditLog.target_type == entity_type)
        
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.filter(AuditLog.created_at >= start_dt)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.filter(AuditLog.created_at <= end_dt)
        except ValueError:
            pass
            
    return query.order_by(desc(AuditLog.created_at))


def _ensure_course_audit_access(db: Session, current_user: TokenData, course_id: str) -> None:
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.org_id == current_user.org_id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role == "category_admin" and course.category_slug != current_user.category_scope:
        raise HTTPException(status_code=404, detail="Course not found")


def _serialize_audit_log(log: AuditLog) -> dict:
    metadata = _metadata(log)
    return {
        "id": f"audit-{log.id}",
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "actor_name": log.actor_name,
        "user_id": log.actor_user_id,
        "action": log.action,
        "entity_type": log.target_type,
        "entity_id": log.target_id,
        "summary": log.message or _generate_summary(log),
        "course_id": metadata.get("course_id"),
        "before_json": metadata.get("before_json"),
        "after_json": metadata.get("after_json"),
    }


def _builder_entity_type(action: str) -> str:
    normalized = action.lower()
    for entity in ("block", "module", "section", "course", "version", "builder"):
        if normalized.startswith(entity):
            return entity
    return "builder"


def _builder_activity_items(
    db: Session,
    current_user: TokenData,
    course_id: str,
    action: str | None,
    user_id: str | None,
    entity_type: str | None,
    start_date: str | None,
    end_date: str | None,
) -> list[dict]:
    query = db.query(BuilderActivityLog).filter(
        BuilderActivityLog.org_id == current_user.org_id,
        BuilderActivityLog.course_id == course_id,
    )
    if action:
        query = query.filter(BuilderActivityLog.action.ilike(f"%{action}%"))
    if user_id:
        query = query.filter(BuilderActivityLog.user_id == user_id)
    if start_date:
        try:
            query = query.filter(BuilderActivityLog.created_at >= datetime.fromisoformat(start_date.replace("Z", "+00:00")))
        except ValueError:
            pass
    if end_date:
        try:
            query = query.filter(BuilderActivityLog.created_at <= datetime.fromisoformat(end_date.replace("Z", "+00:00")))
        except ValueError:
            pass

    activity_logs = query.order_by(desc(BuilderActivityLog.created_at)).all()
    actor_ids = {entry.user_id for entry in activity_logs if entry.user_id}
    actor_names = {
        user.id: user.full_name
        for user in db.query(User).filter(User.id.in_(actor_ids)).all()
    } if actor_ids else {}

    items = []
    for entry in activity_logs:
        resolved_entity_type = _builder_entity_type(entry.action)
        if entity_type and resolved_entity_type != entity_type:
            continue
        try:
            payload = json.loads(entry.payload) if entry.payload else {}
        except (TypeError, ValueError):
            payload = {}
        entity_id = payload.get(f"{resolved_entity_type}_id") or payload.get("block_id") or course_id
        items.append({
            "id": f"builder-{entry.id}",
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "actor_name": actor_names.get(entry.user_id, entry.user_id or "System"),
            "user_id": entry.user_id,
            "action": entry.action.lower().replace("_", "."),
            "entity_type": resolved_entity_type,
            "entity_id": str(entity_id),
            "summary": entry.action.replace("_", " ").title(),
            "course_id": course_id,
            "before_json": None,
            "after_json": payload or None,
        })
    return items


def _course_audit_items(
    db: Session,
    current_user: TokenData,
    course_id: str,
    action: str | None,
    user_id: str | None,
    entity_type: str | None,
    start_date: str | None,
    end_date: str | None,
) -> list[dict]:
    _ensure_course_audit_access(db, current_user, course_id)
    canonical_logs = _build_audit_query(
        db, current_user, course_id, action, user_id, entity_type, start_date, end_date
    ).all()
    items = [_serialize_audit_log(log) for log in canonical_logs]
    items.extend(_builder_activity_items(
        db, current_user, course_id, action, user_id, entity_type, start_date, end_date
    ))
    return sorted(items, key=lambda item: item["created_at"] or "", reverse=True)

@audit_router.get("", dependencies=[Depends(require_capability("audit.view"))])
def list_audit_logs(
    course_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    if course_id:
        all_items = _course_audit_items(
            db, current_user, course_id, action, user_id, entity_type, start_date, end_date
        )
        total = len(all_items)
        offset = (page - 1) * page_size
        items = all_items[offset:offset + page_size]
    else:
        if current_user.role == "category_admin":
            raise HTTPException(status_code=403, detail="A course ID is required for category audit access")
        query = _build_audit_query(db, current_user, None, action, user_id, entity_type, start_date, end_date)
        total = query.count()
        offset = (page - 1) * page_size
        items = [_serialize_audit_log(log) for log in query.offset(offset).limit(page_size).all()]
        
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@audit_router.get("/export", dependencies=[Depends(require_capability("audit.export"))])
def export_audit_logs(
    course_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    if course_id:
        items = _course_audit_items(
            db, current_user, course_id, action, user_id, entity_type, start_date, end_date
        )[:5000]
    else:
        if current_user.role == "category_admin":
            raise HTTPException(status_code=403, detail="A course ID is required for category audit access")
        query = _build_audit_query(db, current_user, None, action, user_id, entity_type, start_date, end_date)
        items = [_serialize_audit_log(log) for log in query.limit(5000).all()]
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Actor", "Action", "Entity Type", "Entity ID", "Summary"])
    
    for log in items:
        writer.writerow([
            log["id"],
            log["created_at"] or "",
            log["actor_name"],
            log["action"],
            log["entity_type"],
            log["entity_id"],
            log["summary"],
        ])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"}
    )
