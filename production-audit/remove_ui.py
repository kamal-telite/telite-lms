import sys

def remove_lines(filepath, start_line, end_line):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Lines are 1-indexed, lists are 0-indexed
    # We want to remove from start_line to end_line INCLUSIVE
    new_lines = lines[:start_line-1] + lines[end_line:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

# 1. PlatformAdminPage.jsx removals
p1 = r"c:\Users\kamal\OneDrive\Desktop\Production\Telite-LMS\telite-frontend\src\pages\platform-admin\PlatformAdminPage.jsx"
# Remove Global Sync Status (line 3030)
remove_lines(p1, 3030, 3030)
# Remove Moodle API Bridge (lines 3009-3012)
remove_lines(p1, 3009, 3012)
# Remove MoodleSyncTab (lines 2351-2790)
remove_lines(p1, 2351, 2790)

# 2. CategoryAdminTabs.jsx removals
p2 = r"c:\Users\kamal\OneDrive\Desktop\Production\Telite-LMS\telite-frontend\src\components\dashboard\CategoryAdminTabs.jsx"
# Remove Moodle Connection Panel (lines 94-117)
remove_lines(p2, 94, 118) # 118 is the empty line after it
# Remove moodleStatus state (line 89)
remove_lines(p2, 89, 89)

print("UI cleanup complete.")
