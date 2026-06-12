import csv
from datetime import datetime
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.models.audit_log import AuditLog
from app.models.user import User
from app.core.permissions import require_capability

audit_router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit Logs"])

def _generate_summary(log: AuditLog) -> str:
    action = log.action.lower()
    entity = log.entity_type.replace("_", " ").title()
    
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

def _build_audit_query(db: Session, current_user: TokenData, course_id: str = None, action: str = None, user_id: str = None, entity_type: str = None, start_date: str = None, end_date: str = None):
    query = db.query(AuditLog, User).outerjoin(User, User.id == AuditLog.user_id).filter(
        AuditLog.org_id == current_user.org_id
    )

    if course_id:
        query = query.filter(AuditLog.course_id == course_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
        
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
    query = _build_audit_query(db, current_user, course_id, action, user_id, entity_type, start_date, end_date)
    
    total = query.count()
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()
    
    items = []
    for log, user in results:
        actor_name = f"{user.first_name} {user.last_name}".strip() if user else log.user_id
        items.append({
            "id": log.id,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "actor_name": actor_name,
            "user_id": log.user_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "summary": _generate_summary(log),
            "before_json": log.before_json,
            "after_json": log.after_json
        })
        
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
    query = _build_audit_query(db, current_user, course_id, action, user_id, entity_type, start_date, end_date)
    results = query.limit(5000).all() # Cap at 5000 for export safety
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Actor", "Action", "Entity Type", "Entity ID", "Summary"])
    
    for log, user in results:
        actor_name = f"{user.first_name} {user.last_name}".strip() if user else log.user_id
        writer.writerow([
            log.id,
            log.created_at.isoformat() if log.created_at else "",
            actor_name,
            log.action,
            log.entity_type,
            log.entity_id,
            _generate_summary(log)
        ])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"}
    )
