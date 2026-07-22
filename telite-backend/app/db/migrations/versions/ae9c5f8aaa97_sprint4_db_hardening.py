"""sprint4_db_hardening

Revision ID: ae9c5f8aaa97
Revises: f2c3f178fd8b
Create Date: 2026-07-22 17:37:46.331294

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'ae9c5f8aaa97'
down_revision = 'f2c3f178fd8b'
branch_labels = None
depends_on = None


def _has_fk(inspector, table_name, constraint_name):
    try:
        fks = inspector.get_foreign_keys(table_name)
        for fk in fks:
            if fk.get('name') == constraint_name:
                return True
    except Exception:
        pass
    return False


def _has_index(inspector, table_name, index_name):
    try:
        indexes = inspector.get_indexes(table_name)
        for ix in indexes:
            if ix.get('name') == index_name:
                return True
    except Exception:
        pass
    return False


def upgrade():
    context = op.get_context()
    if context.as_sql:
        # Offline mode: assume we need to apply everything and generate the SQL
        # Idempotency is up to the runner (though Alembic usually assumes schema doesn't have it)
        op.create_index('ix_learning_path_courses_course_id', 'learning_path_courses', ['course_id'])
        op.create_foreign_key('fk_notifications_user_id', 'notifications', 'users', ['user_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('fk_pal_quiz_scores_user_id', 'pal_quiz_scores', 'users', ['user_id'], ['id'], ondelete='SET NULL')
        op.create_foreign_key('fk_allowed_domains_org_id', 'allowed_domains', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('fk_password_reset_tokens_user_id', 'password_reset_tokens', 'users', ['user_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('fk_password_reset_tokens_org_id', 'password_reset_tokens', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')
        return

    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # 1. Indexes (TD-029)
    if not _has_index(inspector, 'learning_path_courses', 'ix_learning_path_courses_course_id'):
        op.create_index('ix_learning_path_courses_course_id', 'learning_path_courses', ['course_id'])

    # 2. Foreign Keys (TD-028)
    if not _has_fk(inspector, 'notifications', 'fk_notifications_user_id'):
        op.create_foreign_key('fk_notifications_user_id', 'notifications', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    if not _has_fk(inspector, 'pal_quiz_scores', 'fk_pal_quiz_scores_user_id'):
        op.create_foreign_key('fk_pal_quiz_scores_user_id', 'pal_quiz_scores', 'users', ['user_id'], ['id'], ondelete='SET NULL')

    if not _has_fk(inspector, 'allowed_domains', 'fk_allowed_domains_org_id'):
        op.create_foreign_key('fk_allowed_domains_org_id', 'allowed_domains', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')

    if not _has_fk(inspector, 'password_reset_tokens', 'fk_password_reset_tokens_user_id'):
        op.create_foreign_key('fk_password_reset_tokens_user_id', 'password_reset_tokens', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    if not _has_fk(inspector, 'password_reset_tokens', 'fk_password_reset_tokens_org_id'):
        op.create_foreign_key('fk_password_reset_tokens_org_id', 'password_reset_tokens', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')


def downgrade():
    context = op.get_context()
    if context.as_sql:
        op.drop_index('ix_learning_path_courses_course_id', table_name='learning_path_courses')
        op.drop_constraint('fk_notifications_user_id', 'notifications', type_='foreignkey')
        op.drop_constraint('fk_allowed_domains_org_id', 'allowed_domains', type_='foreignkey')
        op.drop_constraint('fk_pal_quiz_scores_user_id', 'pal_quiz_scores', type_='foreignkey')
        op.drop_constraint('fk_password_reset_tokens_user_id', 'password_reset_tokens', type_='foreignkey')
        op.drop_constraint('fk_password_reset_tokens_org_id', 'password_reset_tokens', type_='foreignkey')
        return

    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    if _has_fk(inspector, 'password_reset_tokens', 'fk_password_reset_tokens_org_id'):
        op.drop_constraint('fk_password_reset_tokens_org_id', 'password_reset_tokens', type_='foreignkey')

    if _has_fk(inspector, 'password_reset_tokens', 'fk_password_reset_tokens_user_id'):
        op.drop_constraint('fk_password_reset_tokens_user_id', 'password_reset_tokens', type_='foreignkey')

    if _has_fk(inspector, 'allowed_domains', 'fk_allowed_domains_org_id'):
        op.drop_constraint('fk_allowed_domains_org_id', 'allowed_domains', type_='foreignkey')

    if _has_fk(inspector, 'pal_quiz_scores', 'fk_pal_quiz_scores_user_id'):
        op.drop_constraint('fk_pal_quiz_scores_user_id', 'pal_quiz_scores', type_='foreignkey')

    if _has_fk(inspector, 'notifications', 'fk_notifications_user_id'):
        op.drop_constraint('fk_notifications_user_id', 'notifications', type_='foreignkey')

    if _has_index(inspector, 'learning_path_courses', 'ix_learning_path_courses_course_id'):
        op.drop_index('ix_learning_path_courses_course_id', table_name='learning_path_courses')
