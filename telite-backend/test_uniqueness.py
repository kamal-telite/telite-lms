import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.repositories.course_repo import CourseRepository, CategoryRepository, DuplicateResourceError
from app.repositories.org_repo import OrgRepository
from app.models.organization import Organization
from app.models.category import Category

engine = create_engine('postgresql://postgres:postgres123@localhost:55432/telite_backend')
Session = sessionmaker(bind=engine)
session = Session()

try:
    org_repo = OrgRepository(session)
    cat_repo = CategoryRepository(session)
    course_repo = CourseRepository(session)

    # Clean up previous runs
    session.execute(text("DELETE FROM courses WHERE name = 'Python Foundations'"))
    session.execute(text("DELETE FROM categories WHERE name = 'Test Cat A' OR name = 'Test Cat B'"))
    session.execute(text("DELETE FROM organizations WHERE name = 'Org A' OR name = 'Org B'"))
    session.commit()

    print("Creating Org A and Org B...")
    org_a = org_repo.create_organization(name="Org A", slug="org-a", plan="enterprise")
    org_b = org_repo.create_organization(name="Org B", slug="org-b", plan="enterprise")
    session.commit()
    print("Org A ID:", org_a.id, "Org B ID:", org_b.id)

    print("Creating Categories...")
    cat_a = cat_repo.create_category(name="Test Cat A", org_id=org_a.id)
    cat_b = cat_repo.create_category(name="Test Cat B", org_id=org_b.id)
    session.commit()

    print("Test 1: Create 'Python Foundations' in Org A")
    course_a = course_repo.create_course(name="Python Foundations", category_slug=cat_a.slug, org_id=org_a.id)
    session.commit()
    print("Success: Course A created with slug:", course_a.slug)

    print("Test 2: Create 'Python Foundations' in Org B")
    course_b = course_repo.create_course(name="Python Foundations", category_slug=cat_b.slug, org_id=org_b.id)
    session.commit()
    print("Success: Course B created with slug:", course_b.slug)

    print("Test 3: Duplicate course in Org A (should fail)")
    try:
        course_repo.create_course(name="Python Foundations", category_slug=cat_a.slug, org_id=org_a.id)
        print("FAIL: Allowed duplicate course creation in the same tenant!")
    except DuplicateResourceError as e:
        print("Success: Caught DuplicateResourceError correctly ->", e.message)
    except Exception as e:
        print("FAIL: Caught unexpected exception:", type(e))

except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    session.close()
