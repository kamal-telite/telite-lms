import os
import sys
import json
import zipfile
import tempfile
import time
from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient

sys.path.append("/app")
from app.main import app

def create_dummy_h5p(title: str, main_library: str) -> str:
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, f"{title.replace(' ', '_')}.h5p")
    h5p_json = {
        "title": title,
        "language": "en",
        "mainLibrary": main_library,
        "embedTypes": ["div"],
        "preloadedDependencies": [{"machineName": main_library, "majorVersion": 1, "minorVersion": 0}]
    }
    content_json = {"score": 100}
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("h5p.json", json.dumps(h5p_json))
        zf.writestr("content/content.json", json.dumps(content_json))
    return zip_path

def run_verification():
    client = TestClient(app)
    engine = create_engine("postgresql+psycopg://postgres:postgres123@postgres:5432/telite_backend")
    
    print("\n--- Phase 0: Checking Permissions ---")
    with engine.connect() as conn:
        res = conn.execute(text("SELECT permission_key FROM role_permissions WHERE role='category_admin' ORDER BY permission_key;"))
        perms = [r[0] for r in res.fetchall()]
        print("Permissions for category_admin:")
        for p in perms:
            if p.startswith('h5p.') or p.startswith('media.'):
                print(f" - {p}")

    print("\n--- Logging in as Category Admin ---")
    login_res = client.post("/auth/login", data={"username": "kt_category_admin", "password": "KTCategory@1234"})
    admin_token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print("\n--- A. H5P Upload ---")
    h5p_path_v1 = create_dummy_h5p("Python Quiz V1", "H5P.MultiChoice")
    with open(h5p_path_v1, "rb") as f:
        upload_res = client.post("/authoring/media/upload", headers=admin_headers, files={"file": ("quiz_v1.h5p", f, "application/x-h5p")})
    
    if upload_res.status_code != 200:
        print("Upload failed:", upload_res.text)
        return
        
    asset_id = upload_res.json()["asset"]["id"]
    print(f"Uploaded Asset ID: {asset_id}")
    
    with engine.connect() as conn:
        res = conn.execute(text(f"SELECT id, filename, asset_version, metadata_json FROM media_assets WHERE id = {asset_id};"))
        row = res.fetchone()
        print("DB Evidence (media_assets):")
        print(f" ID: {row[0]}")
        print(f" Filename: {row[1]}")
        print(f" Version: {row[2]}")
        print(f" Metadata: {json.dumps(row[3], indent=2)}")

    print("\n--- B. H5P Attachment (Create Course & Block) ---")
    # 1. Create Course
    course_res = client.post("/authoring/courses", headers=admin_headers, json={"title": "H5P Test Course", "category_id": 1})
    course_id = course_res.json()["id"]
    # 2. Create Section
    sec_res = client.post(f"/authoring/courses/{course_id}/sections", headers=admin_headers, json={"title": "Section 1", "sort_order": 0})
    sec_id = sec_res.json()["id"]
    # 3. Create Module
    mod_res = client.post(f"/authoring/modules", headers=admin_headers, json={"section_id": sec_id, "title": "Module 1", "sort_order": 0})
    mod_id = mod_res.json()["id"]
    # 4. Create Block
    block_payload = {
        "module_id": mod_id,
        "block_type": "h5p",
        "media_asset_id": asset_id,
        "sort_order": 0,
        "content": "Test H5P",
        "settings": {
            "asset_id": asset_id,
            "asset_version": 1,
            "metadata": row[3]
        }
    }
    block_res = client.post(f"/authoring/blocks", headers=admin_headers, json=block_payload)
    block_id = block_res.json()["id"]
    
    with engine.connect() as conn:
        res = conn.execute(text(f"SELECT block_type, media_asset_id, settings FROM lesson_blocks WHERE id = '{block_id}';"))
        row = res.fetchone()
        print("DB Evidence (lesson_blocks):")
        print(f" Block Type: {row[0]}")
        print(f" Media Asset ID: {row[1]}")
        print(f" Settings: {json.dumps(row[2], indent=2)}")

    print("\n--- Publishing Course ---")
    pub_res = client.post(f"/authoring/publishing/courses/{course_id}/workflow", headers=admin_headers, json={"action": "publish"})
    if pub_res.status_code != 200:
        print("Publish failed:", pub_res.text)
        return
    print("Course published successfully.")

    print("\n--- C. Learner Runtime & D. Progress ---")
    print("Logging in as Learner 1...")
    learner_login = client.post("/auth/login", data={"username": "kt_learner_1", "password": "KTLearner@1234"})
    learner_token = learner_login.json()["access_token"]
    learner_headers = {"Authorization": f"Bearer {learner_token}"}
    
    # Send events
    client.post("/api/v1/learner/events", headers=learner_headers, json={
        "events": [
            {"event_type": "H5P_STARTED", "course_id": course_id, "module_id": mod_id, "block_id": block_id},
            {"event_type": "H5P_COMPLETED", "course_id": course_id, "module_id": mod_id, "block_id": block_id}
        ]
    })
    print("Sent H5P_STARTED and H5P_COMPLETED events.")
    
    with engine.connect() as conn:
        res = conn.execute(text("SELECT event_type FROM learner_events WHERE event_type LIKE 'H5P_%' ORDER BY created_at DESC LIMIT 2;"))
        events = [r[0] for r in res.fetchall()]
        print("DB Evidence (learner_events):", events)
        
        res = conn.execute(text(f"SELECT status, completion_percentage FROM lesson_block_progress WHERE block_id = '{block_id}';"))
        prog = res.fetchone()
        print("DB Evidence (lesson_block_progress):")
        if prog:
            print(f" Status: {prog[0]}, Completion: {prog[1]}%")
        else:
            print(" No progress found.")

    print("\n--- E. Version Freeze Test ---")
    print("Replacing Asset with V2...")
    h5p_path_v2 = create_dummy_h5p("Python Quiz V2", "H5P.MultiChoice")
    with open(h5p_path_v2, "rb") as f:
        rep_res = client.post(f"/authoring/media/{asset_id}/replace", headers=admin_headers, files={"file": ("quiz_v2.h5p", f, "application/x-h5p")})
    new_version = rep_res.json()["asset"]["asset_version"]
    print(f"Asset Replaced. New Asset Version: {new_version}")
    
    with engine.connect() as conn:
        res = conn.execute(text(f"SELECT snapshot_json FROM course_versions WHERE course_id = '{course_id}' AND status = 'published' ORDER BY created_at DESC LIMIT 1;"))
        snap = res.fetchone()[0]
        snap_asset_ver = snap["sections"][0]["modules"][0]["blocks"][0]["settings"]["asset_version"]
        print(f"Published Course Version uses Asset Version: {snap_asset_ver} (Expected: 1)")
        
    print("Republishing Course...")
    client.post(f"/authoring/publishing/courses/{course_id}/workflow", headers=admin_headers, json={"action": "publish"})
    
    with engine.connect() as conn:
        res = conn.execute(text(f"SELECT snapshot_json FROM course_versions WHERE course_id = '{course_id}' AND status = 'published' ORDER BY created_at DESC LIMIT 1;"))
        snap = res.fetchone()[0]
        snap_asset_ver = snap["sections"][0]["modules"][0]["blocks"][0]["settings"]["asset_version"]
        print(f"Republished Course Version uses Asset Version: {snap_asset_ver} (Expected: 2)")

if __name__ == "__main__":
    run_verification()
