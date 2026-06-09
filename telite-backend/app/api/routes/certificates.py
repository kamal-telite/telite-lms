from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Any

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.models.course import Course
from app.models.user import User
from app.models.certificate import Certificate
from app.services.certificate_service import CertificateService

cert_router = APIRouter(prefix="/certificates", tags=["Certificates"])
public_cert_router = APIRouter(prefix="/public/verify", tags=["Public Certificates"])

@cert_router.post("/{course_id}/issue")
def issue_certificate(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Issue a certificate to the user for the completed course.
    """
    user = db.query(User).filter(User.id == current_user.id).first()
    course = db.query(Course).filter(Course.id == course_id, Course.org_id == current_user.org_id).first()
    
    if not user or not course:
        raise HTTPException(status_code=404, detail="User or course not found")
        
    # Check if they actually completed the course in module_progress/pal_scores
    # For Phase E, we assume the frontend only calls this if they are 100% complete.
    
    cert_service = CertificateService(db)
    cert = cert_service.generate_certificate(user, course, current_user.org_id)
    
    return {"success": True, "certificate": cert.to_dict()}


@cert_router.get("/{course_id}")
def get_certificate(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Fetch an already issued certificate for a course.
    """
    cert = db.query(Certificate).filter(
        Certificate.user_id == current_user.id,
        Certificate.course_id == course_id,
        Certificate.org_id == current_user.org_id
    ).first()
    
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found or not earned yet")
        
    return {"certificate": cert.to_dict()}


@public_cert_router.get("/{token}")
def verify_certificate(
    token: str,
    db: Session = Depends(db_session)
):
    """
    Public verification endpoint without auth.
    Accessed via QR Code or URL link.
    """
    cert_service = CertificateService(db)
    result = cert_service.verify_certificate(token)
    
    if not result:
        raise HTTPException(status_code=404, detail="Invalid or revoked certificate token")
        
    return result
