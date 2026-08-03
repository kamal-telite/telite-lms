"""
Test Assignment Submission Idempotency

Tests that ensure the assignment submission flow is idempotent:
- Duplicate requests do not create duplicate submissions
- Duplicate requests do not create duplicate files
- Duplicate requests do not create duplicate notifications
- Race conditions are handled gracefully
- Concurrent requests return consistent responses
"""

from unittest.mock import Mock, patch, MagicMock
import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.assignment_service import AssignmentService
from app.api.auth import TokenData
from app.models.assignment_submission import AssignmentSubmission


class TestAssignmentSubmissionIdempotency:
    """Test assignment submission idempotency"""
    
    def test_concurrent_submission_handles_integrity_error(self, mock_learner_user, mock_db):
        """Test that concurrent submissions handle IntegrityError gracefully"""
        service = AssignmentService(mock_db)
        
        # Mock the repository methods
        service.repo.get_submission_for_learner = Mock(return_value=None)
        service.repo.save_submission = Mock(side_effect=IntegrityError("duplicate key"))
        service._store_files = Mock(return_value=[])
        service._mark_assignment_complete = Mock()
        
        # Mock storage for cleanup
        service.storage.delete = Mock()
        
        # Mock get_submission_for_learner after the race condition
        def get_submission_after_race(*args, **kwargs):
            existing = Mock(spec=AssignmentSubmission)
            existing.id = 123
            existing.status = "pending_verification"
            existing.to_dict = Mock(return_value={"id": 123, "status": "pending_verification"})
            return existing
        
        service.repo.get_submission_for_learner = Mock(side_effect=[None, get_submission_after_race()])
        
        # Mock progress repository
        with patch('app.services.assignment_service.ProgressRepository') as mock_progress_repo:
            mock_progress_instance = Mock()
            mock_progress_instance.get_course_progress = Mock(return_value=None)
            mock_progress_repo.return_value = mock_progress_instance
            
            # Mock notification repository
            with patch('app.services.assignment_service.NotificationRepository') as mock_notification_repo:
                mock_notification_instance = Mock()
                mock_notification_repo.create = Mock()
                mock_notification_repo.return_value = mock_notification_instance
                
                # This should handle the IntegrityError and return the existing submission
                import asyncio
                result = asyncio.run(service.submit(
                    block_id=1,
                    user=mock_learner_user,
                    submission_text="Test submission",
                    files=[],
                    resubmit=False,
                    existing_file_paths=None
                ))
        
        # Verify the result returns the existing submission
        assert result["message"] == "Assignment submitted successfully"
        assert result["submission"]["id"] == 123
        assert result["submission"]["status"] == "pending_verification"
        
        # Verify database was rolled back
        mock_db.rollback.assert_called_once()
    
    def test_draft_save_handles_integrity_error(self, mock_learner_user, mock_db):
        """Test that concurrent draft saves handle IntegrityError gracefully"""
        service = AssignmentService(mock_db)
        
        # Mock the repository methods
        existing_submission = Mock(spec=AssignmentSubmission)
        existing_submission.status = "draft"
        existing_submission.submission_files_json = []
        
        service.repo.get_submission_for_learner = Mock(return_value=existing_submission)
        service.repo.save_submission = Mock(side_effect=IntegrityError("duplicate key"))
        service._store_files = Mock(return_value=[])
        
        # Mock storage for cleanup
        service.storage.delete = Mock()
        
        # Mock get_submission_for_learner after the race condition
        def get_submission_after_race(*args, **kwargs):
            existing = Mock(spec=AssignmentSubmission)
            existing.id = 456
            existing.status = "draft"
            existing.to_dict = Mock(return_value={"id": 456, "status": "draft"})
            return existing
        
        service.repo.get_submission_for_learner = Mock(side_effect=[existing_submission, get_submission_after_race()])
        
        # This should handle the IntegrityError and return the existing submission
        import asyncio
        result = asyncio.run(service.save_draft(
            block_id=1,
            user=mock_learner_user,
            submission_text="Test draft",
            files=[],
            existing_file_paths=None
        ))
        
        # Verify the result returns the existing submission
        assert result["message"] == "Assignment draft saved"
        assert result["submission"]["id"] == 456
        assert result["submission"]["status"] == "draft"
        
        # Verify database was rolled back
        mock_db.rollback.assert_called_once()
    
    def test_file_cleanup_on_integrity_error(self, mock_learner_user, mock_db):
        """Test that uploaded files are cleaned up on IntegrityError"""
        service = AssignmentService(mock_db)
        
        # Mock uploaded files
        uploaded_files = [
            {"file_path": "/uploads/test/file1.pdf", "filename": "file1.pdf"},
            {"file_path": "/uploads/test/file2.pdf", "filename": "file2.pdf"}
        ]
        
        service._store_files = Mock(return_value=uploaded_files)
        service.repo.get_submission_for_learner = Mock(return_value=None)
        service.repo.save_submission = Mock(side_effect=IntegrityError("duplicate key"))
        service._mark_assignment_complete = Mock()
        service.storage.delete = Mock()
        
        # Mock get_submission_for_learner after the race condition
        def get_submission_after_race(*args, **kwargs):
            existing = Mock(spec=AssignmentSubmission)
            existing.id = 789
            existing.status = "pending_verification"
            existing.to_dict = Mock(return_value={"id": 789, "status": "pending_verification"})
            return existing
        
        service.repo.get_submission_for_learner = Mock(side_effect=[None, get_submission_after_race()])
        
        with patch('app.services.assignment_service.ProgressRepository') as mock_progress_repo:
            mock_progress_instance = Mock()
            mock_progress_instance.get_course_progress = Mock(return_value=None)
            mock_progress_repo.return_value = mock_progress_instance
            
            with patch('app.services.assignment_service.NotificationRepository') as mock_notification_repo:
                mock_notification_instance = Mock()
                mock_notification_repo.create = Mock()
                mock_notification_repo.return_value = mock_notification_instance
                
                import asyncio
                result = asyncio.run(service.submit(
                    block_id=1,
                    user=mock_learner_user,
                    submission_text="Test submission",
                    files=[],
                    resubmit=False,
                    existing_file_paths=None
                ))
        
        # Verify files were cleaned up
        assert service.storage.delete.call_count == 2
        service.storage.delete.assert_any_call("/uploads/test/file1.pdf")
        service.storage.delete.assert_any_call("/uploads/test/file2.pdf")
    
    def test_successful_submission_creates_single_record(self, mock_learner_user, mock_db):
        """Test that successful submission creates exactly one submission record"""
        service = AssignmentService(mock_db)
        
        # Mock successful submission
        submission = Mock(spec=AssignmentSubmission)
        submission.id = 999
        submission.status = "pending_verification"
        submission.to_dict = Mock(return_value={"id": 999, "status": "pending_verification"})
        
        service.repo.get_submission_for_learner = Mock(return_value=None)
        service.repo.save_submission = Mock(return_value=submission)
        service._store_files = Mock(return_value=[])
        service._mark_assignment_complete = Mock()
        
        with patch('app.services.assignment_service.ProgressRepository') as mock_progress_repo:
            mock_progress_instance = Mock()
            mock_progress_instance.get_course_progress = Mock(return_value=None)
            mock_progress_repo.return_value = mock_progress_instance
            
            with patch('app.services.assignment_service.NotificationRepository') as mock_notification_repo:
                mock_notification_instance = Mock()
                mock_notification_repo.create = Mock()
                mock_notification_repo.return_value = mock_notification_instance
                
                import asyncio
                result = asyncio.run(service.submit(
                    block_id=1,
                    user=mock_learner_user,
                    submission_text="Test submission",
                    files=[],
                    resubmit=False,
                    existing_file_paths=None
                ))
        
        # Verify exactly one submission was saved
        service.repo.save_submission.assert_called_once()
        assert result["submission"]["id"] == 999
        
        # Verify notification was created once
        mock_notification_instance.create.assert_called_once()
    
    def test_integrity_error_without_existing_submission_raises_error(self, mock_learner_user, mock_db):
        """Test that IntegrityError without existing submission raises appropriate error"""
        service = AssignmentService(mock_db)
        
        service.repo.get_submission_for_learner = Mock(return_value=None)
        service.repo.save_submission = Mock(side_effect=IntegrityError("duplicate key"))
        service._store_files = Mock(return_value=[])
        service._mark_assignment_complete = Mock()
        service.storage.delete = Mock()
        
        with patch('app.services.assignment_service.ProgressRepository') as mock_progress_repo:
            mock_progress_instance = Mock()
            mock_progress_instance.get_course_progress = Mock(return_value=None)
            mock_progress_repo.return_value = mock_progress_instance
            
            with patch('app.services.assignment_service.NotificationRepository') as mock_notification_repo:
                mock_notification_instance = Mock()
                mock_notification_repo.create = Mock()
                mock_notification_repo.return_value = mock_notification_instance
                
                import asyncio
                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(service.submit(
                        block_id=1,
                        user=mock_learner_user,
                        submission_text="Test submission",
                        files=[],
                        resubmit=False,
                        existing_file_paths=None
                    ))
        
        # Verify appropriate error message
        assert exc_info.value.status_code == 500
        assert "race condition" in str(exc_info.value.detail)


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def mock_learner_user():
    """Create a mock learner user"""
    return TokenData(
        id="learner_123",
        email="learner@example.com",
        role="learner",
        org_id=1,
        is_platform_admin=False,
        permissions=[]
    )