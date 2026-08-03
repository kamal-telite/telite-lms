"""
Test Question Bank Error Handling

Tests that ensure the Question Bank module has improved error handling:
- Database rollback occurs on every failed write
- Generic exceptions are replaced with business exceptions where appropriate
- Comprehensive logging with required context
- Consistent HTTP error responses
"""

from unittest.mock import Mock, patch, MagicMock
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DatabaseError

from app.features.question_bank.crud import (
    create_category,
    update_category,
    delete_category,
    create_tag,
    update_tag,
    delete_tag,
    create_question,
    update_draft_question,
    publish_question,
    create_new_draft_from_published,
    archive_draft_question,
    create_import_job,
)
from app.features.question_bank.schemas import (
    CategoryCreate,
    CategoryUpdate,
    TagCreate,
    TagUpdate,
    QuestionCreate,
    QuestionUpdateDraft,
    ImportJobCreate,
)


class TestQuestionBankErrorHandling:
    """Test Question Bank error handling improvements"""

    def test_create_category_rollback_on_integrity_error(self, mock_db):
        """Test that database rollback occurs on integrity error during category creation"""
        req = CategoryCreate(name="Test Category", parent_id=None)
        
        mock_db.add = Mock(side_effect=IntegrityError("unique constraint violation"))
        mock_db.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            create_category(mock_db, org_id=1, req=req)
        
        assert exc_info.value.status_code == 409
        assert "unique" in str(exc_info.value.detail).lower()
        mock_db.rollback.assert_called_once()

    def test_create_category_rollback_on_database_error(self, mock_db):
        """Test that database rollback occurs on database error during category creation"""
        req = CategoryCreate(name="Test Category", parent_id=None)
        
        mock_db.add = Mock(side_effect=DatabaseError("connection timeout"))
        mock_db.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            create_category(mock_db, org_id=1, req=req)
        
        assert exc_info.value.status_code == 500
        assert "database error" in str(exc_info.value.detail).lower()
        mock_db.rollback.assert_called_once()

    def test_update_category_rollback_on_integrity_error(self, mock_db):
        """Test that database rollback occurs on integrity error during category update"""
        req = CategoryUpdate(name="Updated Category")
        
        mock_category = Mock()
        mock_category.id = 1
        mock_category.name = "Old Name"
        mock_category.parent_id = None
        
        mock_db.execute = Mock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_category)))
        mock_db.commit = Mock(side_effect=IntegrityError("unique constraint violation"))
        mock_db.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            update_category(mock_db, org_id=1, category_id=1, req=req)
        
        assert exc_info.value.status_code == 409
        mock_db.rollback.assert_called_once()

    def test_delete_category_rollback_on_database_error(self, mock_db):
        """Test that database rollback occurs on database error during category deletion"""
        mock_category = Mock()
        mock_category.id = 1
        
        mock_db.execute = Mock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_category)))
        mock_db.execute.return_value = Mock(scalar_one=Mock(return_value=0))
        mock_db.delete = Mock(side_effect=DatabaseError("connection timeout"))
        mock_db.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            delete_category(mock_db, org_id=1, category_id=1)
        
        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()

    def test_create_tag_rollback_on_integrity_error(self, mock_db):
        """Test that database rollback occurs on integrity error during tag creation"""
        req = TagCreate(name="Test Tag")
        
        mock_db.add = Mock(side_effect=IntegrityError("unique constraint violation"))
        mock_db.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            create_tag(mock_db, org_id=1, req=req)
        
        assert exc_info.value.status_code == 409
        mock_db.rollback.assert_called_once()

    def test_update_tag_rollback_on_database_error(self, mock_db):
        """Test that database rollback occurs on database error during tag update"""
        req = TagUpdate(name="Updated Tag")
        
        mock_tag = Mock()
        mock_tag.id = 1
        mock_tag.name = "Old Name"
        
        mock_db.execute = Mock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_tag)))
        mock_db.commit = Mock(side_effect=DatabaseError("connection timeout"))
        mock_db.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            update_tag(mock_db, org_id=1, tag_id=1, req=req)
        
        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()

    def test_delete_tag_rollback_on_integrity_error(self, mock_db):
        """Test that database rollback occurs on integrity error during tag deletion"""
        mock_tag = Mock()
        mock_tag.id = 1
        
        mock_db.execute = Mock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_tag)))
        mock_db.execute.return_value = Mock(scalar_one=Mock(return_value=0))
        mock_db.delete = Mock(side_effect=IntegrityError("foreign key constraint"))
        mock_db.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            delete_tag(mock_db, org_id=1, tag_id=1)
        
        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()

    def test_create_question_rollback_on_integrity_error(self, mock_db):
        """Test that database rollback occurs on integrity error during question creation"""
        req = QuestionCreate(
            category_id=None,
            tag_ids=[],
            question_type="multiple_choice",
            question_text="Test question?",
            points=10,
            options_json=[],
            correct_answer_json=["A"]
        )
        
        with patch('app.features.question_bank.crud.QuestionBankService') as mock_service_class:
            mock_service = Mock()
            mock_service.create_question = Mock(side_effect=IntegrityError("foreign key constraint"))
            mock_service_class.return_value = mock_service
            
            mock_db.rollback = Mock()
            
            with pytest.raises(HTTPException) as exc_info:
                create_question(mock_db, org_id=1, bank_id=1, req=req)
            
            assert exc_info.value.status_code == 409
            mock_db.rollback.assert_called_once()

    def test_update_draft_question_rollback_on_database_error(self, mock_db):
        """Test that database rollback occurs on database error during draft update"""
        req = QuestionUpdateDraft(question_text="Updated text")
        
        with patch('app.features.question_bank.crud.QuestionBankService') as mock_service_class:
            mock_service = Mock()
            mock_question = Mock()
            mock_question.bank_id = 1
            mock_question.current_draft_version_id = 1
            mock_service.question_repo.get_by_id_and_org = Mock(return_value=mock_question)
            
            mock_draft = Mock()
            mock_draft.id = 1
            mock_draft.status = "DRAFT"
            mock_service.version_repo.get_by_id_and_org = Mock(return_value=mock_draft)
            
            mock_db.commit = Mock(side_effect=DatabaseError("connection timeout"))
            mock_db.rollback = Mock()
            
            mock_service_class.return_value = mock_service
            
            with pytest.raises(HTTPException) as exc_info:
                update_draft_question(mock_db, org_id=1, bank_id=1, q_id=1, req=req)
            
            assert exc_info.value.status_code == 500
            mock_db.rollback.assert_called_once()

    def test_publish_question_rollback_on_integrity_error(self, mock_db):
        """Test that database rollback occurs on integrity error during question publish"""
        with patch('app.features.question_bank.crud.QuestionBankService') as mock_service_class:
            mock_service = Mock()
            mock_version = Mock()
            mock_version.id = 1
            mock_service.publish_question = Mock(return_value=mock_version)
            
            mock_db.commit = Mock(side_effect=IntegrityError("constraint violation"))
            mock_db.rollback = Mock()
            
            mock_service_class.return_value = mock_service
            
            with pytest.raises(HTTPException) as exc_info:
                publish_question(mock_db, org_id=1, q_id=1)
            
            assert exc_info.value.status_code == 409
            mock_db.rollback.assert_called_once()

    def test_create_new_draft_rollback_on_database_error(self, mock_db):
        """Test that database rollback occurs on database error during draft creation"""
        with patch('app.features.question_bank.crud.QuestionBankService') as mock_service_class:
            mock_service = Mock()
            mock_question = Mock()
            mock_question.bank_id = 1
            mock_question.current_published_version_id = 1
            mock_service.question_repo.get_by_id_and_org = Mock(return_value=mock_question)
            
            mock_version = Mock()
            mock_version.id = 2
            mock_service.edit_published_question = Mock(return_value=mock_version)
            
            mock_db.commit = Mock(side_effect=DatabaseError("connection timeout"))
            mock_db.rollback = Mock()
            
            mock_service_class.return_value = mock_service
            
            with pytest.raises(HTTPException) as exc_info:
                create_new_draft_from_published(mock_db, org_id=1, bank_id=1, q_id=1)
            
            assert exc_info.value.status_code == 500
            mock_db.rollback.assert_called_once()

    def test_archive_draft_rollback_on_database_error(self, mock_db):
        """Test that database rollback occurs on database error during draft archive"""
        with patch('app.features.question_bank.crud.QuestionBankService') as mock_service_class:
            mock_service = Mock()
            mock_service.archive_draft = Mock()
            
            mock_db.commit = Mock(side_effect=DatabaseError("connection timeout"))
            mock_db.rollback = Mock()
            
            mock_service_class.return_value = mock_service
            
            with pytest.raises(HTTPException) as exc_info:
                archive_draft_question(mock_db, org_id=1, q_id=1)
            
            assert exc_info.value.status_code == 500
            mock_db.rollback.assert_called_once()

    def test_create_import_job_rollback_on_integrity_error(self, mock_db):
        """Test that database rollback occurs on integrity error during import job creation"""
        req = ImportJobCreate(
            file_key="test-file.csv",
            category_id=None,
            tag_ids=[]
        )
        
        mock_db.add = Mock(side_effect=IntegrityError("unique constraint violation"))
        mock_db.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            create_import_job(mock_db, org_id=1, user_id="user123", req=req)
        
        assert exc_info.value.status_code == 409
        mock_db.rollback.assert_called_once()

    def test_http_exception_not_rolled_back(self, mock_db):
        """Test that HTTP exceptions are not rolled back (they are expected validation errors)"""
        req = CategoryUpdate(name="Updated Category")
        
        mock_db.execute = Mock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))
        mock_db.rollback = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            update_category(mock_db, org_id=1, category_id=1, req=req)
        
        assert exc_info.value.status_code == 404
        # HTTPException should not trigger rollback
        mock_db.rollback.assert_not_called()

    def test_successful_category_creation_logs_info(self, mock_db):
        """Test that successful category creation logs appropriate info"""
        req = CategoryCreate(name="Test Category", parent_id=None)
        
        mock_category = Mock()
        mock_category.id = 1
        mock_category.name = "Test Category"
        mock_category.parent_id = None
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        with patch('app.features.question_bank.crud.logger') as mock_logger:
            create_category(mock_db, org_id=1, req=req)
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Category created successfully" in call_args[0][0]
            assert call_args[1]['extra']['org_id'] == 1
            assert call_args[1]['extra']['category_id'] == 1
            assert call_args[1]['extra']['operation'] == 'create_category'

    def test_failed_category_creation_logs_error(self, mock_db):
        """Test that failed category creation logs appropriate error"""
        req = CategoryCreate(name="Test Category", parent_id=None)
        
        mock_db.add = Mock(side_effect=IntegrityError("unique constraint violation"))
        mock_db.rollback = Mock()
        
        with patch('app.features.question_bank.crud.logger') as mock_logger:
            with pytest.raises(HTTPException):
                create_category(mock_db, org_id=1, req=req)
            
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Database integrity error" in call_args[0][0]
            assert call_args[1]['extra']['org_id'] == 1
            assert call_args[1]['extra']['error_type'] == 'IntegrityError'
            assert call_args[1]['extra']['operation'] == 'create_category'


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    return Mock(spec=Session)