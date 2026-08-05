import sqlalchemy as sa

engine = sa.create_engine('postgresql+psycopg://postgres:postgres123@localhost:55432/telite_backend')
with engine.begin() as conn:
    conn.execute(sa.text("UPDATE users SET password_hash = '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW' WHERE id IN ('kt_superadmin', 'kt_category_admin', 'kt_learner_2');"))
    print("Passwords updated!")
