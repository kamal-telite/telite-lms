from locust import HttpUser, task, between

class TeliteUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # We simulate a user hitting public or lightly protected endpoints
        pass

    @task(3)
    def test_health(self):
        self.client.get("/health")

    @task(2)
    def test_public_branding(self):
        # Hits the public branding API to simulate unauthenticated access
        self.client.get("/api/public/branding/tenanta")

    @task(1)
    def test_invalid_login(self):
        # Simulate an invalid login to hit the auth route and rate limiter
        self.client.post("/auth/login", data={"username": "loadtest", "password": "badpassword"})
