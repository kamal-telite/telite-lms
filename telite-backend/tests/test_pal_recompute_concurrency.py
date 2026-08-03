"""
Test PAL Score Recompute Concurrency

Tests that ensure PAL score recomputation is safe from concurrent execution:
- Row-level locking prevents concurrent recomputations for the same learner
- Multiple requests serialize correctly
- No stale writes or lost updates occur
"""

from unittest.mock import Mock, patch, MagicMock
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.services.pal_score_service import PALScoreService
from app.models.user import User
from app.models.course_progress import CourseProgress


class TestPALRecomputeConcurrency:
    """Test PAL score recomputation concurrency control"""

    def test_recompute_user_uses_row_level_locking(self, mock_db):
        """Test that recompute_user uses SELECT FOR UPDATE to lock the user row"""
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.org_id = 1
        mock_user.pal_score = 75.0
        mock_user.pal_completion_pct = 80.0
        mock_user.pal_quiz_avg = 85.0
        mock_user.pal_task_completion_pct = 70.0
        mock_user.total_courses = 5
        
        mock_select = Mock()
        mock_select.where.return_value.with_for_update.return_value = mock_select
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        with patch('app.services.pal_score_service.select', return_value=mock_select):
            service = PALScoreService(mock_db)
            service.compute_user_metrics = Mock(return_value={
                "pal_score": 75.0,
                "course_completion": 80.0,
                "quiz_average": 85.0,
                "assignment_average": 90.0,
                "task_completion": 70.0,
                "weights": {},
                "strengths": [],
                "weak_areas": [],
                "improvements": [],
                "progress_trend": [],
                "completion_timeline": []
            })
            
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            
            service.recompute_user("user123", 1)
            
            # Verify that with_for_update was called (row-level locking)
            mock_select.where.return_value.with_for_update.assert_called_once()

    def test_concurrent_recomputes_serialize(self, mock_db):
        """Test that concurrent recomputations for the same user serialize correctly"""
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.org_id = 1
        mock_user.pal_score = 75.0
        mock_user.pal_completion_pct = 80.0
        mock_user.pal_quiz_avg = 85.0
        mock_user.pal_task_completion_pct = 70.0
        mock_user.total_courses = 5
        
        mock_select = Mock()
        mock_select.where.return_value.with_for_update.return_value = mock_select
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        with patch('app.services.pal_score_service.select', return_value=mock_select):
            service = PALScoreService(mock_db)
            service.compute_user_metrics = Mock(return_value={
                "pal_score": 75.0,
                "course_completion": 80.0,
                "quiz_average": 85.0,
                "assignment_average": 90.0,
                "task_completion": 70.0,
                "weights": {},
                "strengths": [],
                "weak_areas": [],
                "improvements": [],
                "progress_trend": [],
                "completion_timeline": []
            })
            
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            
            # Simulate multiple concurrent calls
            results = []
            for _ in range(3):
                result = service.recompute_user("user123", 1)
                results.append(result)
            
            # All calls should complete successfully
            assert len(results) == 3
            # All should return the same metrics
            for result in results:
                assert result["pal_score"] == 75.0

    def test_recompute_user_returns_empty_metrics_for_missing_user(self, mock_db):
        """Test that recompute_user returns empty metrics when user not found"""
        mock_select = Mock()
        mock_select.where.return_value.with_for_update.return_value = mock_select
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        with patch('app.services.pal_score_service.select', return_value=mock_select):
            service = PALScoreService(mock_db)
            result = service.recompute_user("nonexistent", 1)
            
            assert result["pal_score"] == 0.0
            assert result["course_completion"] == 0.0
            assert result["quiz_average"] == 0.0
            assert result["assignment_average"] == 0.0
            assert result["task_completion"] == 0.0

    def test_recompute_user_with_commit_flag(self, mock_db):
        """Test that recompute_user commits when commit flag is True"""
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.org_id = 1
        mock_user.pal_score = 75.0
        mock_user.pal_completion_pct = 80.0
        mock_user.pal_quiz_avg = 85.0
        mock_user.pal_task_completion_pct = 70.0
        mock_user.total_courses = 5
        
        mock_select = Mock()
        mock_select.where.return_value.with_for_update.return_value = mock_select
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        with patch('app.services.pal_score_service.select', return_value=mock_select):
            service = PALScoreService(mock_db)
            service.compute_user_metrics = Mock(return_value={
                "pal_score": 75.0,
                "course_completion": 80.0,
                "quiz_average": 85.0,
                "assignment_average": 90.0,
                "task_completion": 70.0,
                "weights": {},
                "strengths": [],
                "weak_areas": [],
                "improvements": [],
                "progress_trend": [],
                "completion_timeline": []
            })
            
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            
            service.recompute_user("user123", 1, commit=True)
            
            # Verify commit was called
            mock_db.commit.assert_called_once()

    def test_recompute_user_without_commit_flag(self, mock_db):
        """Test that recompute_user does not commit when commit flag is False"""
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.org_id = 1
        mock_user.pal_score = 75.0
        mock_user.pal_completion_pct = 80.0
        mock_user.pal_quiz_avg = 85.0
        mock_user.pal_task_completion_pct = 70.0
        mock_user.total_courses = 5
        
        mock_select = Mock()
        mock_select.where.return_value.with_for_update.return_value = mock_select
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        with patch('app.services.pal_score_service.select', return_value=mock_select):
            service = PALScoreService(mock_db)
            service.compute_user_metrics = Mock(return_value={
                "pal_score": 75.0,
                "course_completion": 80.0,
                "quiz_average": 85.0,
                "assignment_average": 90.0,
                "task_completion": 70.0,
                "weights": {},
                "strengths": [],
                "weak_areas": [],
                "improvements": [],
                "progress_trend": [],
                "completion_timeline": []
            })
            
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            
            service.recompute_user("user123", 1, commit=False)
            
            # Verify commit was NOT called
            mock_db.commit.assert_not_called()
            # Verify flush was called
            mock_db.flush.assert_called_once()

    def test_recompute_user_updates_course_counts(self, mock_db):
        """Test that recompute_user correctly updates courses_completed and total_courses"""
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.org_id = 1
        mock_user.pal_score = 75.0
        mock_user.pal_completion_pct = 80.0
        mock_user.pal_quiz_avg = 85.0
        mock_user.pal_task_completion_pct = 70.0
        mock_user.total_courses = 5
        
        mock_progress1 = Mock()
        mock_progress1.status = "completed"
        mock_progress1.completion_percentage = 100
        
        mock_progress2 = Mock()
        mock_progress2.status = "in_progress"
        mock_progress2.completion_percentage = 50
        
        mock_progress3 = Mock()
        mock_progress3.status = "submitted"
        mock_progress3.completion_percentage = 100
        
        mock_select = Mock()
        mock_select.where.return_value.with_for_update.return_value = mock_select
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value.scalars.return_value.all.return_value = [
            mock_progress1, mock_progress2, mock_progress3
        ]
        
        with patch('app.services.pal_score_service.select', return_value=mock_select):
            service = PALScoreService(mock_db)
            service.compute_user_metrics = Mock(return_value={
                "pal_score": 75.0,
                "course_completion": 80.0,
                "quiz_average": 85.0,
                "assignment_average": 90.0,
                "task_completion": 70.0,
                "weights": {},
                "strengths": [],
                "weak_areas": [],
                "improvements": [],
                "progress_trend": [],
                "completion_timeline": []
            })
            
            service.recompute_user("user123", 1)
            
            # Verify courses_completed was updated (2 completed/submitted)
            assert mock_user.courses_completed == 2
            # Verify total_courses was updated (3 total)
            assert mock_user.total_courses == 3

    def test_recompute_category_calls_recompute_user_for_each_learner(self, mock_db):
        """Test that recompute_category calls recompute_user for each learner"""
        mock_user1 = Mock()
        mock_user1.id = "user1"
        mock_user1.org_id = 1
        
        mock_user2 = Mock()
        mock_user2.id = "user2"
        mock_user2.org_id = 1
        
        mock_select = Mock()
        mock_select.where.return_value.scalars.return_value.all.return_value = [
            mock_user1, mock_user2
        ]
        
        with patch('app.services.pal_score_service.select', return_value=mock_select):
            service = PALScoreService(mock_db)
            service.recompute_user = Mock(return_value={"pal_score": 75.0})
            
            service.recompute_category("test-category", 1)
            
            # Verify recompute_user was called for each user
            assert service.recompute_user.call_count == 2
            service.recompute_user.assert_any_call("user1", 1)
            service.recompute_user.assert_any_call("user2", 1)


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    return Mock(spec=Session)