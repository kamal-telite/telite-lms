import requests

base_url = "http://localhost:8001/auth"
accounts = [
    ("globaladmin", "GlobalAdmin@1234"),
    ("kt_superadmin", "KTSuper@1234"),
    ("kt_category_admin", "KTCategory@1234"),
    ("kt_learner_1", "KTLearner@1234"),
    ("kt_learner_2", "KTLearner@1234"),
    ("kt_learner_3", "KTLearner@1234")
]

all_success = True
for user, pwd in accounts:
    try:
        r = requests.post(f"{base_url}/login", data={"username": user, "password": pwd}, timeout=5)
        if r.status_code == 200:
            print(f"SUCCESS: {user} logged in")
        else:
            print(f"FAIL: {user} failed -> {r.status_code} {r.text}")
            all_success = False
    except Exception as e:
        print(f"ERROR: {user} -> {str(e)}")
        all_success = False

if all_success:
    print("ALL ACCOUNTS LOGGED IN SUCCESSFULLY")
