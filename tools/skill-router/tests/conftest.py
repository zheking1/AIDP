"""
AIDP Test Utilities
Provides fixtures for cleaning up test data
"""

import asyncio
import pytest
import httpx


TEST_PREFIXES = ("test-", "test_", "integration-")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def base_url():
    """Base URL for API tests."""
    return "http://127.0.0.1:8788"


@pytest.fixture(scope="session")
def api_client(base_url):
    """HTTP client for API tests."""
    with httpx.Client(base_url=base_url, timeout=30) as client:
        yield client


@pytest.fixture(scope="session")
def admin_token(api_client):
    """Login as admin and get session cookie."""
    resp = api_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if resp.status_code == 200:
        return api_client.cookies
    return None


class TestDataCleaner:
    """Helper class for cleaning test data."""
    
    def __init__(self, db_container="novel-postgres", db_user="novel_os", db_name="novel_os"):
        self.db_container = db_container
        self.db_user = db_user
        self.db_name = db_name
    
    def clear_all(self):
        """Clear all test data."""
        import subprocess
        
        tables = ["skill", "rule", "llm_model", "evolution", "review", "operation_log"]
        
        for table in tables:
            for prefix in TEST_PREFIXES:
                cmd = [
                    "docker", "exec", self.db_container,
                    "psql", "-U", self.db_user, "-d", self.db_name,
                    "-c", f"DELETE FROM {table} WHERE name LIKE '{prefix}%' OR title LIKE '{prefix}%';"
                ]
                subprocess.run(cmd, capture_output=True)
        
        print("Test data cleared")
    
    def clear_table(self, table_name: str):
        """Clear test data from a specific table."""
        import subprocess
        
        # Determine column to check based on table
        columns = {
            "skill": "name",
            "rule": "name",
            "llm_model": "name",
            "evolution": "title",
            "review": "summary",
            "operation_log": "action"
        }
        
        col = columns.get(table_name, "name")
        
        for prefix in TEST_PREFIXES:
            cmd = [
                "docker", "exec", self.db_container,
                "psql", "-U", self.db_user, "-d", self.db_name,
                "-c", f"DELETE FROM {table_name} WHERE {col} LIKE '{prefix}%';"
            ]
            subprocess.run(cmd, capture_output=True)
        
        print(f"Cleared test data from {table_name}")


@pytest.fixture(scope="session")
def cleaner():
    """Provide TestDataCleaner instance."""
    return TestDataCleaner()


@pytest.fixture(autouse=True)
def cleanup_after_test(request, cleaner):
    """Automatically clean test data after each test."""
    yield
    # Cleanup happens after test completes
    # Only clean if test failed (to help debug)
    if request.node.rep_call and request.node.rep_call.failed:
        print(f"\nTest {request.node.name} failed, cleaning up...")
        cleaner.clear_all()
