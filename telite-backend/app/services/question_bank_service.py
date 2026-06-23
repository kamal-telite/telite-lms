from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.repositories.question_bank_repo import QuestionBankRepository
from app.repositories.question_repo import QuestionRepository, QuestionVersionRepository
from app.models.question import Question, QuestionVersion
from app.models.question_bank import QuestionBank

class QuestionBankService:
    def __init__(self, session: Session):
        self.session = session
        self.bank_repo = QuestionBankRepository(session)
        self.question_repo = QuestionRepository(session)
        self.version_repo = QuestionVersionRepository(session)

    def create_question(self, org_id: int, bank_id: int, category_id: Optional[int], question_type: str, question_text: str, points: int, options_json: List[Dict[str, Any]], correct_answer_json: List[str]) -> Question:
        """Create a new question and its initial DRAFT version."""
        # 1. Create the base Question
        question = self.question_repo.create(
            org_id=org_id,
            bank_id=bank_id,
            category_id=category_id
        )
        
        # 2. Create the initial DRAFT version
        version = self.version_repo.create(
            org_id=org_id,
            question_id=question.id,
            category_id=category_id,
            version_number=1,
            question_type=question_type,
            question_text=question_text,
            options_json=options_json,
            correct_answer_json=correct_answer_json,
            points=points,
            status="DRAFT"
        )
        
        # 3. Link draft to question
        self.question_repo.update(question, current_draft_version_id=version.id)
        
        return question

    def publish_question(self, org_id: int, question_id: int) -> QuestionVersion:
        """Publish the current draft version."""
        question = self.question_repo.get_by_id_and_org(question_id, org_id)
        if not question:
            raise ValueError("Question not found")
        if not question.current_draft_version_id:
            raise ValueError("No draft version exists for this question")
            
        draft_version = self.version_repo.get_by_id_and_org(question.current_draft_version_id, org_id)
        if not draft_version or draft_version.status != "DRAFT":
            raise ValueError("Draft version not found or invalid status")
            
        # Update version status
        self.version_repo.update(draft_version, status="PUBLISHED")
        
        # Update question pointers
        self.question_repo.update(
            question, 
            current_published_version_id=draft_version.id
        )
        
        return draft_version

    def edit_published_question(self, org_id: int, question_id: int, updates: Dict[str, Any]) -> QuestionVersion:
        """Edit a published question by creating a new DRAFT version."""
        question = self.question_repo.get_by_id_and_org(question_id, org_id)
        if not question:
            raise ValueError("Question not found")
            
        if not question.current_published_version_id:
            raise ValueError("Question is not published yet, edit the draft instead.")
            
        current_published = self.version_repo.get_by_id_and_org(question.current_published_version_id, org_id)
        if not current_published:
            raise ValueError("Published version not found")
            
        # If there's already an active draft, we could update it or reject.
        # But we create a new DRAFT version based on the published + updates.
        latest_version_num = self.version_repo.get_latest_version_number(question_id, org_id)
        
        new_version_num = latest_version_num + 1
        
        new_version = self.version_repo.create(
            org_id=org_id,
            question_id=question_id,
            category_id=updates.get("category_id", current_published.category_id),
            version_number=new_version_num,
            question_type=updates.get("question_type", current_published.question_type),
            question_text=updates.get("question_text", current_published.question_text),
            options_json=updates.get("options_json", current_published.options_json),
            correct_answer_json=updates.get("correct_answer_json", current_published.correct_answer_json),
            points=updates.get("points", current_published.points),
            status="DRAFT"
        )
        
        self.question_repo.update(question, current_draft_version_id=new_version.id)
        
        return new_version

    def archive_draft(self, org_id: int, question_id: int) -> QuestionVersion:
        """Archive a draft version. Cannot archive the active published version."""
        question = self.question_repo.get_by_id_and_org(question_id, org_id)
        if not question:
            raise ValueError("Question not found")
            
        if not question.current_draft_version_id:
            raise ValueError("No draft version to archive")
            
        # If draft IS the published version (i.e. they are the same), reject.
        if question.current_draft_version_id == question.current_published_version_id:
            raise ValueError("Cannot archive an active published version. Unpublish or create a new draft first.")
            
        draft_version = self.version_repo.get_by_id_and_org(question.current_draft_version_id, org_id)
        if not draft_version:
            raise ValueError("Draft version not found")
            
        if draft_version.status == "PUBLISHED":
             raise ValueError("Cannot archive an active published version. Unpublish or create a new draft first.")
             
        self.version_repo.update(draft_version, status="ARCHIVED")
        self.question_repo.update(question, current_draft_version_id=None)
        
        return draft_version
