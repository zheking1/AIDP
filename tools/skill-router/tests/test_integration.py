"""
AIDP Integration Tests
Tests the API endpoints with automatic cleanup
"""

import pytest
import httpx


class TestHealth:
    """Test health endpoints."""
    
    def test_skillrouter_health(self, api_client):
        """Test SkillRouter health endpoint."""
        resp = api_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
    
    def test_knowledge_tool_health(self):
        """Test knowledge-tool health endpoint."""
        with httpx.Client(timeout=5) as client:
            resp = client.get("http://127.0.0.1:18081/health")
            assert resp.status_code == 200
    
    def test_sandbox_tool_health(self):
        """Test sandbox-tool health endpoint."""
        with httpx.Client(timeout=5) as client:
            resp = client.get("http://127.0.0.1:18083/health")
            assert resp.status_code == 200
    
    def test_quality_tool_health(self):
        """Test quality-tool health endpoint."""
        with httpx.Client(timeout=5) as client:
            resp = client.get("http://127.0.0.1:18084/health")
            assert resp.status_code == 200
    
    def test_memory_tool_health(self):
        """Test memory-tool health endpoint."""
        with httpx.Client(timeout=5) as client:
            resp = client.get("http://127.0.0.1:18085/health")
            assert resp.status_code == 200
    
    def test_controller_health(self):
        """Test controller health endpoint."""
        with httpx.Client(timeout=5) as client:
            resp = client.get("http://127.0.0.1:8883/health")
            assert resp.status_code == 200


class TestAuth:
    """Test authentication."""
    
    def test_login_success(self, api_client):
        """Test successful login."""
        resp = api_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert resp.status_code == 200
    
    def test_login_failure(self, api_client):
        """Test failed login."""
        resp = api_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrong_password"
        })
        assert resp.status_code == 401


class TestSkills:
    """Test skill CRUD operations."""
    
    def test_create_skill(self, api_client, admin_token):
        """Test creating a skill."""
        if not admin_token:
            pytest.skip("Not logged in")
        
        resp = api_client.post("/api/skills", json={
            "name": "test-integration-skill",
            "description": "A test skill",
            "content": "# Test Skill\n\nThis is a test."
        })
        assert resp.status_code in [200, 201, 409]  # 409 if already exists
    
    def test_list_skills(self, api_client, admin_token):
        """Test listing skills."""
        if not admin_token:
            pytest.skip("Not logged in")
        
        resp = api_client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))


class TestControllerTools:
    """Test controller tool management."""
    
    def test_list_tools(self):
        """Test listing registered tools."""
        with httpx.Client(timeout=5) as client:
            resp = client.get("http://127.0.0.1:8883/api/tools")
            assert resp.status_code == 200
            tools = resp.json()
            assert len(tools) >= 4  # At least our 4 tools
    
    def test_health_check_all(self):
        """Test health check for all tools."""
        with httpx.Client(timeout=10) as client:
            resp = client.get("http://127.0.0.1:8883/api/tools/health/all")
            assert resp.status_code == 200
            results = resp.json()
            assert all(r["status"] == "healthy" for r in results)


class TestSandbox:
    """Test sandbox execution."""
    
    def test_execute_python(self):
        """Test Python code execution."""
        with httpx.Client(timeout=10) as client:
            resp = client.post("http://127.0.0.1:18083/api/execute", json={
                "code": "print(42)",
                "language": "python"
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["exitCode"] == 0
            assert "42" in data["stdout"]


class TestQuality:
    """Test quality checks."""
    
    def test_lint_check(self):
        """Test lint check."""
        with httpx.Client(timeout=10) as client:
            resp = client.post("http://127.0.0.1:18084/api/check", json={
                "code": "x = 1\n",
                "checkType": "lint"
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "issues" in data


class TestMemory:
    """Test memory operations."""
    
    def test_create_and_search(self):
        """Test creating and searching memory."""
        with httpx.Client(timeout=10) as client:
            # Create
            resp = client.post("http://127.0.0.1:18085/api/memory", json={
                "project": "test-integration",
                "category": "test",
                "title": "test-integration-memory",
                "content": "Test content"
            })
            assert resp.status_code == 200
            
            # Search
            resp = client.post("http://127.0.0.1:18085/api/memory/search", 
                params={"project": "test-integration", "query": "test"})
            assert resp.status_code == 200
            results = resp.json()
            assert len(results) > 0
