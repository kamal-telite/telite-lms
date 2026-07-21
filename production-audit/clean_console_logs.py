import re

filepath = r"c:\Users\kamal\OneDrive\Desktop\Production\Telite-LMS\telite-frontend\src\pages\learner\LearnerPage.jsx"
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "console.log" in line and ("LearnerPage mounted" in line or "STATE CHANGED" in line or "RENDER" in line or "FETCH START" in line or "RAW RESPONSE" in line or "RESPONSE DATA" in line or "CERTIFICATES" in line or "IS ARRAY" in line or "STATE SET" in line or "Certificates refreshed" in line):
        continue
    new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Console logs cleaned.")
