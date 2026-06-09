import hashlib
import uuid
import logging
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session

# Try importing WeasyPrint and qrcode, but don't fail hard if not installed locally
try:
    from weasyprint import HTML, CSS
    import qrcode
    import qrcode.image.svg
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from app.models.certificate import Certificate
from app.models.organization_branding import OrganizationBranding
from app.models.user import User
from app.models.course import Course

logger = logging.getLogger("telite.certificates")

class CertificateService:
    def __init__(self, db: Session):
        self.db = db

    def generate_certificate(self, user: User, course: Course, org_id: int) -> Certificate:
        """
        Generate a new certificate for the user and course.
        1. Generates verification token and hash
        2. Generates QR code
        3. Renders HTML with tenant branding
        4. Converts to PDF via WeasyPrint
        5. Saves to S3 and database
        """
        # Check if already issued
        existing_cert = self.db.query(Certificate).filter(
            Certificate.user_id == user.id,
            Certificate.course_id == course.id,
            Certificate.org_id == org_id
        ).first()
        
        if existing_cert:
            return existing_cert
            
        # 1. Generate token and hash
        token = uuid.uuid4().hex
        cert_hash = self._generate_hash(user, course, token)
        
        # 2. Fetch branding
        branding = self.db.query(OrganizationBranding).filter(
            OrganizationBranding.organization_id == org_id
        ).first()
        
        # 3. Generate QR code
        qr_url = f"https://telite.io/verify/{token}"
        
        # 4. Generate PDF
        pdf_bytes = self._generate_pdf(user, course, branding, qr_url, cert_hash)
        
        # 5. Save to S3 (Mocked for now)
        pdf_s3_key = f"tenant_{org_id}/certificates/{course.id}/{user.id}_{token}.pdf"
        self._upload_to_s3(pdf_s3_key, pdf_bytes)
        
        # 6. Save to DB
        cert = Certificate(
            id=str(uuid.uuid4()),
            user_id=user.id,
            course_id=course.id,
            org_id=org_id,
            pdf_s3_key=pdf_s3_key,
            certificate_hash=cert_hash,
            verification_token=token,
            qr_code_url=qr_url,
            issued_version=1,
            issued_at=datetime.utcnow()
        )
        self.db.add(cert)
        self.db.commit()
        self.db.refresh(cert)
        
        return cert

    def verify_certificate(self, token: str) -> dict[str, Any] | None:
        """Verify a certificate by token."""
        cert = self.db.query(Certificate).filter(Certificate.verification_token == token).first()
        if not cert:
            return None
            
        user = self.db.query(User).filter(User.id == cert.user_id).first()
        course = self.db.query(Course).filter(Course.id == cert.course_id).first()
        
        return {
            "valid": True,
            "issued_to": user.full_name if user else "Unknown User",
            "course_name": course.name if course else "Unknown Course",
            "issued_at": cert.issued_at.isoformat(),
            "hash": cert.certificate_hash,
            "pdf_url": f"https://cdn.telite.io/{cert.pdf_s3_key}"
        }

    def _generate_hash(self, user: User, course: Course, token: str) -> str:
        """Create a cryptographic hash of the certificate details for tamper evidence."""
        data_string = f"{user.id}:{user.email}:{course.id}:{token}"
        return hashlib.sha256(data_string.encode('utf-8')).hexdigest()

    def _generate_pdf(self, user: User, course: Course, branding: OrganizationBranding, qr_url: str, cert_hash: str) -> bytes:
        """Render HTML and convert to PDF using WeasyPrint."""
        primary_color = branding.certificate_primary_color if branding and branding.certificate_primary_color else "#000000"
        signature_url = branding.certificate_signature_url if branding and branding.certificate_signature_url else ""
        
        html_content = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: sans-serif; text-align: center; margin: 50px; border: 10px solid {primary_color}; padding: 50px; }}
                    h1 {{ color: {primary_color}; }}
                    .qr-code {{ position: absolute; bottom: 50px; right: 50px; width: 100px; height: 100px; }}
                    .hash {{ font-size: 10px; color: #888; position: absolute; bottom: 20px; left: 50px; }}
                </style>
            </head>
            <body>
                <h1>Certificate of Completion</h1>
                <p>This is to certify that</p>
                <h2>{user.full_name}</h2>
                <p>has successfully completed the course</p>
                <h2>{course.name}</h2>
                
                <img src="{signature_url}" height="50" style="margin-top: 50px;" />
                <p>Authorized Signature</p>
                
                <div class="hash">Hash: {cert_hash}</div>
                <!-- Mock QR Code layout -->
                <div class="qr-code">
                    <img src="https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={qr_url}" alt="QR Code" />
                </div>
            </body>
        </html>
        """
        
        if WEASYPRINT_AVAILABLE:
            pdf_bytes = HTML(string=html_content).write_pdf()
        else:
            logger.warning("WeasyPrint not installed. Generating mock PDF bytes.")
            pdf_bytes = b"%PDF-1.4 Mock PDF"
            
        return pdf_bytes

    def _upload_to_s3(self, key: str, data: bytes):
        """Mock S3 upload."""
        logger.info(f"Uploading PDF to S3 key: {key} (size: {len(data)} bytes)")
        pass
