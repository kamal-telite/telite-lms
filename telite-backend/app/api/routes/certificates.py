from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.models.course import Course
from app.models.user import User
from app.models.certificate import Certificate
from app.models.notification import NotificationType
from app.repositories.notification_repo import NotificationRepository
from app.core.notification_payloads import (
    certificate_awarded_idempotency_key,
    certificate_awarded_metadata,
)
from app.services.certificate_service import CertificateService
from app.services.completion_policy_service import CompletionPolicyService

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
        
    eligibility = CompletionPolicyService(db).is_certificate_eligible(
        user_id=current_user.id,
        course_id=course_id,
        org_id=current_user.org_id,
    )
    if not eligibility.eligible:
        raise HTTPException(status_code=403, detail="Course must be completed before issuing a certificate")
    
    cert_service = CertificateService(db)
    cert, created = cert_service.generate_certificate(user, course, current_user.org_id)
    if created:
        metadata = certificate_awarded_metadata(
            course_id=cert.course_id,
            certificate_id=cert.id,
            verification_token=cert.verification_token,
        )
        NotificationRepository(db).create_once(
            user_id=cert.user_id,
            org_id=cert.org_id,
            title="Certificate Awarded",
            body=f"Your certificate for {course.name} is ready.",
            notif_type=NotificationType.CERTIFICATE_AWARDED,
            source_type="certificate",
            source_id=cert.id,
            metadata=metadata,
            idempotency_key=certificate_awarded_idempotency_key(
                user_id=cert.user_id,
                certificate_id=cert.id,
            ),
        )
        db.commit()
    
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


@cert_router.get("/{course_id}/download")
def download_certificate(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Download the certificate PDF for a course.
    Returns the PDF file directly.
    """
    cert = db.query(Certificate).filter(
        Certificate.user_id == current_user.id,
        Certificate.course_id == course_id,
        Certificate.org_id == current_user.org_id
    ).first()
    
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found or not earned yet")
    
    # In production, this would fetch the PDF from S3
    # For now, regenerate the PDF on-the-fly
    from app.services.certificate_service import CertificateService
    cert_service = CertificateService(db)
    
    user = db.query(User).filter(User.id == cert.user_id).first()
    course = db.query(Course).filter(Course.id == cert.course_id).first()
    
    if not user or not course:
        raise HTTPException(status_code=404, detail="User or course not found")
    
    from app.models.organization_branding import OrganizationBranding
    branding = db.query(OrganizationBranding).filter(
        OrganizationBranding.organization_id == cert.org_id
    ).first()
    
    qr_url = cert.qr_code_url or f"https://telite.io/verify/{cert.verification_token}"
    pdf_bytes = cert_service._generate_pdf(user, course, branding, qr_url, cert.certificate_hash)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=certificate_{course_id}_{user.id}.pdf"
        }
    )


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
