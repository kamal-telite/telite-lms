from app.db.engine import get_engine
from app.models.certificate import Certificate
from sqlalchemy.orm import sessionmaker
from app.core.storage_paths import certificate_upload_root

engine = get_engine()
Session = sessionmaker(bind=engine)
s = Session()
print('DB_URL', engine.url)
cert = s.query(Certificate).order_by(Certificate.issued_at.desc()).first()
print('CERT_FOUND', bool(cert))
if cert:
    print('CERT_ID', cert.id)
    print('USER_ID', cert.user_id)
    print('COURSE_ID', cert.course_id)
    print('ORG_ID', cert.org_id)
    print('PDF_S3_KEY', cert.pdf_s3_key)
    print('TOKEN', cert.verification_token)
    print('ROOT', certificate_upload_root())
    path = (certificate_upload_root() / cert.pdf_s3_key).resolve()
    print('PATH_EXISTS', path.exists())
    print('PATH', path)
    if path.exists():
        print('SIZE', path.stat().st_size)
