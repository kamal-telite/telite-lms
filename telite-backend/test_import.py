import sys
print("sys.path:", sys.path)
try:
    import app.api.auth
    print("Found auth at:", app.api.auth.__file__)
    print("Has cookie name?", hasattr(app.api.auth, '_account_refresh_cookie_name'))
except Exception as e:
    print("Error:", e)
