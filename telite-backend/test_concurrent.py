import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.repositories.course_repo import CourseRepository, CategoryRepository, DuplicateResourceError
from app.repositories.org_repo import OrgRepository


def concurrent_create(thread_id, org_id, category_slug):
    engine = create_engine('postgresql://postgres:postgres123@localhost:55432/telite_backend')
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        repo = CourseRepository(session)
        # Attempt to create the same course
        course = repo.create_course(
            name="Race Condition Course",
            category_slug=category_slug,
            org_id=org_id,
            description="Testing race conditions",
            tier="free"
        )
        session.commit()
        print(f"[Thread {thread_id}] SUCCESS: Course created.")
    except DuplicateResourceError as e:
        print(f"[Thread {thread_id}] Handled DuplicateResourceError: {e.message}")
        session.rollback()
    except IntegrityError as e:
        print(f"[Thread {thread_id}] FAILED: Leaked IntegrityError! {e}")
        session.rollback()
    except Exception as e:
        print(f"[Thread {thread_id}] Unexpected Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    engine = create_engine('postgresql://postgres:postgres123@localhost:55432/telite_backend')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Setup test data
    org_repo = OrgRepository(session)
    cat_repo = CategoryRepository(session)
    
    session.execute(text("DELETE FROM courses WHERE name = 'Race Condition Course'"))
    session.commit()
    
    # We will use Org A and Test Cat A from the previous script
    # For simplicity, we just fetch any existing category
    cat = session.execute(text("SELECT slug, org_id FROM categories LIMIT 1")).fetchone()
    session.close()
    
    if not cat:
        print("No category found to test with.")
        exit(1)
        
    cat_slug, org_id = cat[0], cat[1]
    
    print(f"Starting concurrent creation test for category: {cat_slug} (Org {org_id})")
    
    # Run 5 concurrent threads
    threads = []
    for i in range(5):
        t = threading.Thread(target=concurrent_create, args=(i, org_id, cat_slug))
        threads.append(t)
    
    for t in threads:
        t.start()
        
    for t in threads:
        t.join()
        
    print("Concurrent test finished.")
