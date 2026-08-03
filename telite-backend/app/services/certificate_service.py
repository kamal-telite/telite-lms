import hashlib
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from sqlalchemy.orm import Session

from app.core.storage_paths import certificate_upload_root
from app.core.observability import log_background_task_failure

# Try importing WeasyPrint and qrcode, but don't fail hard if not installed locally
try:
    from weasyprint import HTML, CSS
    import qrcode
    import qrcode.image.svg
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    # OSError occurs when GTK/Pango libraries are missing (Windows local dev)
    WEASYPRINT_AVAILABLE = False

from app.models.certificate import Certificate
from app.models.organization_branding import OrganizationBranding
from app.models.user import User
from app.models.course import Course

logger = logging.getLogger("telite.certificates")

class CertificateService:
    def __init__(self, db: Session):
        self.db = db

    def generate_certificate(self, user: User, course: Course, org_id: int, *, commit: bool = False) -> tuple[Certificate, bool]:
        """
        Generate a new certificate for the user and course.
        1. Generates verification token and hash
        2. Generates QR code
        3. Renders HTML with tenant branding
        4. Converts to PDF via WeasyPrint
        5. Saves to S3 and database
        """
        try:
            # Check if already issued
            existing_cert = self.db.query(Certificate).filter(
                Certificate.user_id == user.id,
                Certificate.course_id == course.id,
                Certificate.org_id == org_id
            ).first()
            
            if existing_cert:
                return existing_cert, False
                
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
            
            # 5. Save to local disk storage
            pdf_storage_key = f"org_{org_id}/certificates/{course.id}/{user.id}_{token}.pdf"
            self._save_to_disk(pdf_storage_key, pdf_bytes)
            
            # 6. Save to DB
            cert = Certificate(
                id=str(uuid.uuid4()),
                user_id=user.id,
                course_id=course.id,
                org_id=org_id,
                pdf_s3_key=pdf_storage_key,
                certificate_hash=cert_hash,
                verification_token=token,
                qr_code_url=qr_url,
                issued_version=1,
                issued_at=datetime.now(timezone.utc),
                metadata_json={
                    "issued_to": user.full_name,
                    "course_name": course.name,
                    "course_id": course.id,
                    "user_id": user.id,
                    "verification_token": token,
                    "issued_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            self.db.add(cert)
            self.db.flush()
            if commit:
                self.db.commit()
            self.db.refresh(cert)
            
            return cert, True
        except Exception as e:
            log_background_task_failure(
                task_name="certificate_generation",
                exception=e,
                context={
                    "user_id": user.id,
                    "course_id": course.id,
                    "org_id": org_id,
                },
            )
            raise

    def verify_certificate(self, token: str) -> dict[str, Any] | None:
        """Verify a certificate by token."""
        cert = self.db.query(Certificate).filter(Certificate.verification_token == token).first()
        if not cert:
            return None

        user = self.db.query(User).filter(User.id == cert.user_id).first()
        course = self.db.query(Course).filter(Course.id == cert.course_id).first()
        metadata = cert.metadata_json or {}

        return {
            "valid": True,
            "verification_id": cert.id,
            "issued_to": (user.full_name if user else None) or metadata.get("issued_to") or "Unknown User",
            "course_name": (course.name if course else None) or metadata.get("course_name") or "Unknown Course",
            "issued_at": cert.issued_at.isoformat(),
            "hash": cert.certificate_hash,
            "pdf_url": f"/uploads/certificates/{cert.pdf_s3_key}",
            "verification_token": cert.verification_token,
        }

    def _generate_hash(self, user: User, course: Course, token: str) -> str:
        """Create a cryptographic hash of the certificate details for tamper evidence."""
        data_string = f"{user.id}:{user.email}:{course.id}:{token}"
        return hashlib.sha256(data_string.encode('utf-8')).hexdigest()

    def _generate_pdf(self, user: User, course: Course, branding: OrganizationBranding, qr_url: str, cert_hash: str) -> bytes:
        """Render HTML and convert to PDF using WeasyPrint."""
        primary_color = branding.certificate_primary_color if branding and branding.certificate_primary_color else "#1e40af"
        secondary_color = branding.secondary_color if branding and branding.secondary_color else "#3b82f6"
        logo_url = branding.logo_url if branding and branding.logo_url else ""
        signature_url = branding.certificate_signature_url if branding and branding.certificate_signature_url else ""
        org_name = branding.organization.name if branding and branding.organization else "Telite Learning"
        
        issued_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
        cert_id = cert_hash[:8].upper()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @page {{
                        size: A4 landscape;
                        margin: 0;
                    }}
                    body {{
                        font-family: 'Georgia', 'Times New Roman', serif;
                        margin: 0;
                        padding: 0;
                        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    }}
                    .certificate {{
                        width: 1123px;
                        height: 794px;
                        margin: 0 auto;
                        background: white;
                        position: relative;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                    }}
                    .border {{
                        position: absolute;
                        top: 20px;
                        left: 20px;
                        right: 20px;
                        bottom: 20px;
                        border: 3px solid {primary_color};
                        border-radius: 10px;
                    }}
                    .inner-border {{
                        position: absolute;
                        top: 30px;
                        left: 30px;
                        right: 30px;
                        bottom: 30px;
                        border: 1px solid {secondary_color};
                        border-radius: 5px;
                    }}
                    .corner-decoration {{
                        position: absolute;
                        width: 100px;
                        height: 100px;
                        border: 5px solid {primary_color};
                    }}
                    .corner-top-left {{
                        top: 40px;
                        left: 40px;
                        border-right: none;
                        border-bottom: none;
                    }}
                    .corner-top-right {{
                        top: 40px;
                        right: 40px;
                        border-left: none;
                        border-bottom: none;
                    }}
                    .corner-bottom-left {{
                        bottom: 40px;
                        left: 40px;
                        border-right: none;
                        border-top: none;
                    }}
                    .corner-bottom-right {{
                        bottom: 40px;
                        right: 40px;
                        border-left: none;
                        border-top: none;
                    }}
                    .header {{
                        text-align: center;
                        padding-top: 80px;
                    }}
                    .logo {{
                        max-width: 120px;
                        max-height: 80px;
                        margin-bottom: 20px;
                    }}
                    .title {{
                        font-size: 48px;
                        font-weight: bold;
                        color: {primary_color};
                        text-transform: uppercase;
                        letter-spacing: 4px;
                        margin: 0;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                    }}
                    .subtitle {{
                        font-size: 24px;
                        color: #64748b;
                        margin-top: 10px;
                        font-style: italic;
                    }}
                    .content {{
                        text-align: center;
                        margin-top: 60px;
                    }}
                    .certify-text {{
                        font-size: 20px;
                        color: #475569;
                        margin-bottom: 20px;
                    }}
                    .student-name {{
                        font-size: 56px;
                        font-weight: bold;
                        color: {primary_color};
                        margin: 30px 0;
                        text-decoration: underline;
                        text-decoration-color: {secondary_color};
                        text-decoration-thickness: 3px;
                    }}
                    .course-text {{
                        font-size: 20px;
                        color: #475569;
                        margin-bottom: 20px;
                    }}
                    .course-name {{
                        font-size: 42px;
                        font-weight: bold;
                        color: #1e293b;
                        margin: 20px 0;
                    }}
                    .footer {{
                        position: absolute;
                        bottom: 80px;
                        left: 0;
                        right: 0;
                        display: flex;
                        justify-content: space-between;
                        padding: 0 100px;
                    }}
                    .footer-section {{
                        text-align: center;
                    }}
                    .footer-label {{
                        font-size: 14px;
                        color: #64748b;
                        text-transform: uppercase;
                        letter-spacing: 2px;
                        margin-bottom: 10px;
                    }}
                    .footer-value {{
                        font-size: 18px;
                        color: #1e293b;
                        font-weight: bold;
                    }}
                    .signature {{
                        text-align: center;
                        margin-top: 20px;
                    }}
                    .signature-line {{
                        width: 200px;
                        height: 3px;
                        background: {primary_color};
                        margin: 10px auto;
                    }}
                    .signature-text {{
                        font-size: 14px;
                        color: #64748b;
                    }}
                    .qr-section {{
                        position: absolute;
                        bottom: 80px;
                        right: 80px;
                        text-align: center;
                    }}
                    .qr-code {{
                        width: 100px;
                        height: 100px;
                        border: 2px solid {primary_color};
                        padding: 5px;
                        background: white;
                    }}
                    .qr-text {{
                        font-size: 10px;
                        color: #64748b;
                        margin-top: 5px;
                    }}
                    .watermark {{
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%) rotate(-30deg);
                        font-size: 150px;
                        color: rgba(0,0,0,0.03);
                        font-weight: bold;
                        text-transform: uppercase;
                        pointer-events: none;
                    }}
                </style>
            </head>
            <body>
                <div class="certificate">
                    <div class="border"></div>
                    <div class="inner-border"></div>
                    <div class="corner-decoration corner-top-left"></div>
                    <div class="corner-decoration corner-top-right"></div>
                    <div class="corner-decoration corner-bottom-left"></div>
                    <div class="corner-decoration corner-bottom-right"></div>
                    
                    <div class="watermark">Certificate</div>
                    
                    <div class="header">
                        {f'<img src="{logo_url}" class="logo" alt="Logo" />' if logo_url else ''}
                        <h1 class="title">Certificate of Completion</h1>
                        <p class="subtitle">This certificate is proudly presented to</p>
                    </div>
                    
                    <div class="content">
                        <p class="certify-text">This is to certify that</p>
                        <h2 class="student-name">{user.full_name}</h2>
                        <p class="course-text">has successfully completed the course</p>
                        <h3 class="course-name">{course.name}</h3>
                    </div>
                    
                    <div class="footer">
                        <div class="footer-section">
                            <div class="footer-label">Date Issued</div>
                            <div class="footer-value">{issued_date}</div>
                        </div>
                        <div class="footer-section">
                            <div class="footer-label">Certificate ID</div>
                            <div class="footer-value">{cert_id}</div>
                        </div>
                        <div class="footer-section">
                            <div class="signature">
                                {f'<img src="{signature_url}" height="60" alt="Signature" />' if signature_url else '<div class="signature-line"></div>'}
                                <div class="signature-text">Authorized Signature</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="qr-section">
                        <img src="https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={qr_url}" class="qr-code" alt="QR Code" />
                        <p class="qr-text">Scan to verify</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        if WEASYPRINT_AVAILABLE:
            pdf_bytes = HTML(string=html_content).write_pdf()
        else:
            logger.warning("WeasyPrint not installed. Generating mock PDF bytes.")
            # A minimal valid PDF structure so the browser viewer doesn't error out
            pdf_bytes = (
                b"%PDF-1.4\n"
                b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
                b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
                b"3 0 obj <</Type /Page /MediaBox [0 0 600 400]>> endobj\n"
                b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000056 00000 n \n0000000111 00000 n \n"
                b"trailer <</Size 4 /Root 1 0 R>>\nstartxref\n167\n%%EOF\n"
            )
            
        return pdf_bytes

    def _save_to_disk(self, storage_key: str, data: bytes):
        """Save PDF to local disk storage."""
        upload_root = certificate_upload_root()
        target_path = (upload_root / storage_key).resolve()
        
        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the PDF bytes to disk
        target_path.write_bytes(data)
        
        logger.info(f"Saved PDF to local disk: {target_path} (size: {len(data)} bytes)")
