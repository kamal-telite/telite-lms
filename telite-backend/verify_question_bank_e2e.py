import os
import sys
import json
import asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.models.base import Base
import uuid
from app.models import (
    Organization, User, Course, CourseVersion, CourseModule, LessonBlock,
    QuestionBank, Question, QuestionVersion, QuestionImportJob,
    Category
)
from app.models.learner_event import LearnerEvent
from app.models.lesson_block_progress import LessonBlockProgress
from app.core.security import create_access_token, create_access_payload
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
engine = create_engine("postgresql+psycopg://postgres:postgres123@localhost:5432/telite_backend")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def first_quiz_question(snapshot):
    for section in snapshot.get("sections", []):
        for module in section.get("modules", []):
            for block in module.get("blocks", []):
                if block.get("block_type") == "quiz":
                    questions = block.get("settings", {}).get("questions", [])
                    if questions:
                        return questions[0]
    raise AssertionError("Published snapshot does not contain a hydrated quiz question")

async def run_verification():
    print("Starting E2E Verification...\n")
    db = SessionLocal()
    
    # 0. Clean Setup
    print("--- Setup ---")
    import time
    timestamp = int(time.time())
    course_name = f"E2E Course {timestamp}"
    bank_name = f"E2E Bank {timestamp}"

    org = db.execute(select(Organization)).first()[0]

    cat = db.execute(select(Category).where(Category.slug == "e2e-test")).scalar_one_or_none()
    if not cat:
        cat = Category(id=str(uuid.uuid4()), name="E2E Test Category", slug="e2e-test", org_id=org.id)
        db.add(cat)
        db.commit()
        
    admin = db.execute(select(User).where(User.email == "admin@e2e.com")).scalar_one_or_none()
    if not admin:
        admin = User(id=str(uuid.uuid4()), email="admin@e2e.com", password_hash="foo", role="super_admin", org_id=org.id, full_name="E2E Admin", username="admin_e2e", avatar_initials="EA", gradient_start="a", gradient_end="b")
        db.add(admin)
        db.commit()
        db.refresh(admin)
    elif admin.role != "super_admin":
        admin.role = "super_admin"
        db.commit()
        db.refresh(admin)

    learner = db.execute(select(User).where(User.email == "learner@e2e.com")).scalar_one_or_none()
    if not learner:
        learner = User(id=str(uuid.uuid4()), email="learner@e2e.com", password_hash="foo", role="learner", org_id=org.id, full_name="E2E Learner", username="learner_e2e", avatar_initials="EL", gradient_start="a", gradient_end="b")
        db.add(learner)
        db.commit()
        db.refresh(learner)
        
    admin_token = create_access_token(create_access_payload({
        "id": admin.id, "email": admin.email, "role": admin.role, "org_id": admin.org_id, "full_name": admin.full_name
    }))
    learner_token = create_access_token(create_access_payload({
        "id": learner.id, "email": learner.email, "role": learner.role, "org_id": learner.org_id, "full_name": learner.full_name
    }))
    
    headers = get_auth_headers(admin_token)
    learner_headers = get_auth_headers(learner_token)
    
    # Use the root base_url since routes have different prefixes
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Scenario 1 - Core Publish Flow
        print("\n--- Scenario 1: Core Publish Flow ---")
        
        # 1. Create Question Bank
        res = await client.post("/api/v1/question-banks?category_slug=e2e-test", json={"name": bank_name}, headers=headers)
        if res.status_code != 200 and res.status_code != 201:
            print(f"Failed to create Question Bank: {res.text}")
            res.raise_for_status()
        bank_id = res.json()["id"]
        print(f"1. Created Question Bank: ID {bank_id}")
        
        # 2. Create Question v1
        q_payload = {
            "title": "What is 2+2?",
            "question_text": "Calculate the sum of two and two.",
            "question_type": "multiple_choice",
            "points": 10,
            "options_json": [{"id": "a", "text": "3"}, {"id": "b", "text": "4"}],
            "correct_answer_json": ["b"]
        }
        res = await client.post(f"/api/v1/question-banks/{bank_id}/questions", json=q_payload, headers=headers)
        if res.status_code not in (200, 201):
            print(f"Failed to create Question: {res.text}")
            res.raise_for_status()
        q_id = res.json()["id"]
        v1_draft_id = res.json()["current_draft_version_id"]
        print(f"2. Created Question: ID {q_id}, Draft v{v1_draft_id}")
        
        # 3. Publish Question v1
        res = await client.post(f"/api/v1/question-banks/{bank_id}/questions/{q_id}/publish", headers=headers)
        v1_published_id = res.json()["published_version_id"]
        print(f"3. Published Question: v{v1_published_id}")
        
        # 4. Create Course
        res = await client.post("/categories/e2e-test/courses", json={"name": course_name, "description": "Testing", "tier": "free"}, headers=headers)
        if res.status_code not in (200, 201):
            print(f"Failed to create Course: {res.text}")
            res.raise_for_status()
        course_id = res.json()["id"]
        print(f"4. Created Course: ID {course_id}")
        
        # 4.5 Add Section
        res_section = await client.post(f"/authoring/courses/{course_id}/sections", json={"title": "Section 1", "sort_order": 0}, headers=headers)
        if res_section.status_code not in (200, 201):
            print(f"Failed to create Section: {res_section.text}")
            res_section.raise_for_status()
        section_id = res_section.json()["id"]
        
        # 5. Add Module & hydrate its default Quiz Block with a bank reference.
        res = await client.post(f"/authoring/modules", json={"title": "Module 1", "module_type": "quiz", "course_id": course_id, "section": 1, "section_id": section_id}, headers=headers)
        if res.status_code not in (200, 201):
            print(f"Failed to create Module: {res.text}")
            res.raise_for_status()
        module_id = res.json()["module"]["id"]

        res = await client.get(f"/authoring/courses/{course_id}/modules/{module_id}/blocks", headers=headers)
        if res.status_code != 200:
            print(f"Failed to load default quiz block: {res.text}")
            res.raise_for_status()
        blocks = res.json()["blocks"]
        if not blocks:
            raise AssertionError("Quiz module did not create a default quiz block")
        block_id = blocks[0]["id"]

        res = await client.post(f"/authoring/courses/{course_id}/lock", headers=headers)
        if res.status_code not in (200, 201):
            print(f"Failed to acquire builder lock: {res.text}")
            res.raise_for_status()

        quiz_settings = {
            "passing_score": 80,
            "max_attempts": 3,
            "questions": [
                {
                    "type": "bank_reference",
                    "question_id": q_id,
                    "version_id": v1_published_id,
                }
            ],
        }
        res = await client.put(f"/authoring/courses/{course_id}/blocks", json={
            "blocks": [
                {
                    "id": block_id,
                    "module_id": module_id,
                    "block_type": "quiz",
                    "sort_order": 0,
                    "content": "",
                    "settings": quiz_settings,
                }
            ]
        }, headers=headers)
        if res.status_code not in (200, 201):
            print(f"Failed to update quiz block: {res.text}")
            res.raise_for_status()
        print(f"5/6. Added Quiz Block with Imported Question v{v1_published_id}")
        
        # 7. Publish Course (submit_for_review -> approve -> publish)
        res_submit = await client.post(f"/authoring/publishing/courses/{course_id}/workflow", json={"action": "submit_for_review"}, headers=headers)
        if res_submit.status_code not in (200, 201):
            print(f"Failed to submit course: {res_submit.text}")
            if "validation" in res_submit.text.lower():
                val_res = await client.get(f"/authoring/courses/{course_id}/validate", headers=headers)
                print(f"Validation details: {val_res.text}")
            res_submit.raise_for_status()
            
        res_approve = await client.post(f"/authoring/publishing/courses/{course_id}/workflow", json={"action": "approve"}, headers=headers)
        if res_approve.status_code not in (200, 201):
            print(f"Failed to approve course: {res_approve.text}")
            res_approve.raise_for_status()
            
        res = await client.post(f"/authoring/publishing/courses/{course_id}/workflow", json={"action": "publish"}, headers=headers)
        if res.status_code not in (200, 201):
            print(f"Failed to publish course: {res.text}")
            res.raise_for_status()
        publish_payload = res.json()
        course_version_id = publish_payload.get("version_id") or publish_payload.get("id") or publish_payload["version"]["id"]
        print(f"7. Published Course: Version ID {course_version_id}")
        
        # 8. Inspect CourseVersion.snapshot_json
        cv = db.execute(select(CourseVersion).where(CourseVersion.id == course_version_id)).scalar_one()
        snapshot = cv.snapshot_json
        hydrated_question = first_quiz_question(snapshot)
        
        print("\nVerification Scenario 1 Results:")
        print(f"- Has version_id: {'version_id' in hydrated_question}")
        print(f"- Has question_text: {'question_text' in hydrated_question}")
        print(f"- Is hydrated: {hydrated_question.get('type') != 'bank_reference'}")
        
        # Scenario 2 - Immutability
        print("\n--- Scenario 2: Immutability Verification ---")
        
        # Edit question
        res = await client.post(f"/api/v1/question-banks/{bank_id}/questions/{q_id}/drafts", headers=headers)
        v2_draft_id = res.json()["id"]
        
        res = await client.post(f"/api/v1/question-banks/{bank_id}/questions/{q_id}/publish", headers=headers)
        v2_published_id = res.json()["published_version_id"]
        print(f"Created and published Question v{v2_published_id}")
        
        db.expire_all()
        cv_reloaded = db.execute(select(CourseVersion).where(CourseVersion.id == course_version_id)).scalar_one()
        hydrated_question_reloaded = first_quiz_question(cv_reloaded.snapshot_json)
        
        print(f"Original Course Version still references question version {hydrated_question_reloaded.get('version_id')}")
        assert hydrated_question_reloaded.get("version_id") == v1_published_id
        
        # Scenario 3 - Stale Detection
        print("\n--- Scenario 3: Stale Reference Detection ---")
        ref_v_id = v1_published_id
        res = await client.post("/api/v1/question-banks/check-stale", json={"items": [{"question_id": q_id, "version_id": ref_v_id}]}, headers=headers)
        stale_results = res.json()
        print(f"Stale check results: {stale_results}")
        stale_item = stale_results.get(str(q_id)) or stale_results.get(q_id)
        if not stale_item:
            raise AssertionError(f"Stale check response did not include question {q_id}: {stale_results}")
        is_stale = stale_item["is_stale"]
        latest_v = stale_item["latest_version_id"]
        print(f"Is v{ref_v_id} stale? {is_stale}. Latest is v{latest_v}")
        
        # Re-import and update course
        res = await client.put(f"/authoring/courses/{course_id}/blocks", json={
            "blocks": [
                {
                    "id": block_id,
                    "module_id": module_id,
                    "block_type": "quiz",
                    "sort_order": 0,
                    "content": "",
                    "settings": {
                        "passing_score": 80,
                        "max_attempts": 3,
                        "questions": [
                            {
                                "type": "bank_reference",
                                "question_id": q_id,
                                "version_id": v2_published_id,
                            }
                        ],
                    },
                }
            ]
        }, headers=headers)
        if res.status_code not in (200, 201):
            print(f"Failed to update quiz block to v2: {res.text}")
            res.raise_for_status()
        print("Updated block draft to reference v2")
        
        res_submit2 = await client.post(f"/authoring/publishing/courses/{course_id}/workflow", json={"action": "submit_for_review"}, headers=headers)
        if res_submit2.status_code not in (200, 201):
            print(f"Failed to submit course: {res_submit2.text}")
            res_submit2.raise_for_status()
            
        res_approve2 = await client.post(f"/authoring/publishing/courses/{course_id}/workflow", json={"action": "approve"}, headers=headers)
        if res_approve2.status_code not in (200, 201):
            print(f"Failed to approve course: {res_approve2.text}")
            res_approve2.raise_for_status()
            
        res = await client.post(f"/authoring/publishing/courses/{course_id}/workflow", json={"action": "publish"}, headers=headers)
        if res.status_code not in (200, 201):
            print(f"Failed to republish course: {res.text}")
            res.raise_for_status()
        publish_payload_2 = res.json()
        course_version_2_id = publish_payload_2.get("version_id") or publish_payload_2.get("id") or publish_payload_2["version"]["id"]
        print(f"Published new Course Version: ID {course_version_2_id}")
        
        cv2 = db.execute(select(CourseVersion).where(CourseVersion.id == course_version_2_id)).scalar_one()
        hydrated_v2 = first_quiz_question(cv2.snapshot_json)
        print(f"CV2 references question text: {hydrated_v2.get('question_text')}")
        
        # Scenario 4 - Learner Runtime
        print("\n--- Scenario 4: Learner Runtime ---")
        # Enroll learner
        res = await client.post("/api/v1/enrol/manual", json={
            "full_name": learner.full_name,
            "email": learner.email,
            "enrollment_type": "manual",
            "course_ids": [course_id],
            "note": "Question bank E2E learner runtime",
        }, headers=headers)
        if res.status_code not in (200, 201):
            print(f"Failed to enroll learner: {res.text}")
            res.raise_for_status()
        
        question_key = str(hydrated_v2["id"])
        correct_option_id = hydrated_v2["correct_option_id"]
        
        # Submit learner quiz against the frozen CV2 snapshot.
        res = await client.post(f"/api/v1/learner/blocks/{block_id}/quiz/submit", json={
            "answers": {question_key: correct_option_id}
        }, headers=learner_headers)
        if res.status_code not in (200, 201):
            print(f"Failed to submit learner quiz: {res.text}")
            res.raise_for_status()
        
        submit_data = res.json()
        print(f"Quiz submitted. Data: {submit_data}")
        assert submit_data["passed"] is True
        assert submit_data["score"] == 100
        
        # Check DB records
        db.expire_all()
        event = db.execute(
            select(LearnerEvent).where(
                LearnerEvent.user_id == learner.id,
                LearnerEvent.course_id == course_id,
                LearnerEvent.block_id == block_id,
                LearnerEvent.event_type == "QUIZ_SUBMITTED",
            ).order_by(LearnerEvent.created_at.desc())
        ).scalars().first()
        if not event:
            raise AssertionError("LearnerEvent QUIZ_SUBMITTED was not recorded")

        block_progress = db.execute(
            select(LessonBlockProgress).where(
                LessonBlockProgress.user_id == learner.id,
                LessonBlockProgress.block_id == block_id,
            )
        ).scalars().first()
        if not block_progress:
            raise AssertionError("LessonBlockProgress was not recorded")
        
        print(f"LearnerEvent recorded with score: {event.payload_json.get('score')}")
        print(f"LessonBlockProgress status: {block_progress.status}")
        assert event.payload_json.get("passed") is True
        assert block_progress.status == "completed"
        print("Scenario 4 and 5 Verified.")

if __name__ == "__main__":
    asyncio.run(run_verification())
