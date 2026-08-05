import os
import re

directories = [
    "telite-backend/app/api/routes",
    "telite-backend/app/repositories",
    "telite-backend/app/services",
    "telite-backend/app/workers"
]

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to replace body= with message= only within notification_repo.create(...) or similar
    # A simple regex for any line containing notification_repo.create and body= might be tricky
    # Let's just find lines that match `body=` and replace if they look like notification creations.
    # Actually, we can just replace `body=` with `message=` if the file is one of the target ones
    # EXCEPT for announcement_repo where body=body.strip() is used for Announcements.
    
    if "announcement_repo.py" in filepath:
        return
        
    # We will do a safe manual-like regex: find `notification_repo.create(` or `notification_repo.create_once(`
    # and up to the closing `)`, replace `body=` with `message=`.
    
    def replacer(match):
        return match.group(0).replace('body=', 'message=')
        
    pattern = re.compile(r'notification_repo\.create_once\([^)]*\)|notification_repo\.create\([^)]*\)', re.DOTALL)
    new_content = pattern.sub(replacer, content)
    
    # Also handle `AnalyticsRepository` or any place where we might have missed `notification_repo`
    # Let's just catch all `.create(` that take `body=` if it's near `notif_type=`
    pattern2 = re.compile(r'\.create\([^)]*notif_type=[^)]*\)', re.DOTALL)
    new_content = pattern2.sub(replacer, new_content)
    
    pattern3 = re.compile(r'\.create_once\([^)]*notif_type=[^)]*\)', re.DOTALL)
    new_content = pattern3.sub(replacer, new_content)
    
    # There's also `NotificationRepository(session).create(`
    pattern4 = re.compile(r'NotificationRepository\([^)]*\)\.create\([^)]*\)', re.DOTALL)
    new_content = pattern4.sub(replacer, new_content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Refactored: {filepath}")

for d in directories:
    for root, dirs, files in os.walk(d):
        for file in files:
            if file.endswith(".py"):
                refactor_file(os.path.join(root, file))
