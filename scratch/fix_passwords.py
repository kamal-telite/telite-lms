import hashlib

password = "password"
salt = b"telite-dev-salt"
hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000).hex()
print("Hash is:", hashed)

import sqlalchemy as sa
engine = sa.create_engine('postgresql+psycopg://postgres:postgres123@localhost:55432/telite_backend')
with engine.begin() as conn:
    conn.execute(sa.text(f"UPDATE users SET password_hash = '{hashed}' WHERE id IN ('kt_superadmin', 'kt_category_admin', 'kt_learner_2');"))
    print("Passwords updated!")
