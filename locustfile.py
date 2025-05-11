from locust import HttpUser, task, between
import random
import json
import re
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Test questions
TEST_QUESTIONS = [
    "What are the schedules for computer science courses?",
    "When does the semester start?",
    "How to enroll in a course?",
    "What is the weather today?"
]

class ChatbotUser(HttpUser):
    wait_time = between(1, 5)
    host = "http://192.168.100.201:5000"  # No trailing slash

    def on_start(self):
        # Set timeout for requests
        self.client.timeout = 10  # 10 seconds
        # Fetch CSRF token
        try:
            response = self.client.get("/", name="GET / (fetch CSRF)")
            if response.status_code == 200:
                match = re.search(r'<input[^>]*name="csrf_token"[^>]*value="([^"]*)"[^>]*>', response.text)
                self.csrf_token = match.group(1) if match else None
                if not self.csrf_token:
                    logger.error("Failed to extract CSRF token from HTML")
                    self.csrf_token = "dummy_csrf_token"
                else:
                    logger.debug("Extracted CSRF token: %s", self.csrf_token)
            else:
                logger.error("GET / failed with status %d: %s", response.status_code, response.text)
                self.csrf_token = "dummy_csrf_token"
        except Exception as e:
            logger.error("Error fetching CSRF token: %s", str(e))
            self.csrf_token = "dummy_csrf_token"

    @task
    def send_question(self):
        question = random.choice(TEST_QUESTIONS)
        payload = {
            "message": question,
            "output_lang": "en",
            "csrf_token": self.csrf_token
        }
        headers = {"X-CSRFToken": self.csrf_token}
        with self.client.post("/chat", data=payload, headers=headers, name="POST /chat", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "error" not in data:
                        logger.debug("Successful /chat response: %s", data)
                        response.success()
                    else:
                        logger.error("Error in /chat response: %s", data["error"])
                        response.failure(f"Error in response: {data['error']}")
                except json.JSONDecodeError:
                    logger.error("Invalid JSON response from /chat: %s", response.text)
                    response.failure("Invalid JSON response")
            else:
                logger.error("POST /chat failed with status %d: %s", response.status_code, response.text)
                response.failure(f"HTTP Error: {response.status_code}")