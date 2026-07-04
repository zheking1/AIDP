import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAuthAPI:
    """认证 API 测试"""

    def test_login_success(self):
        """测试登录成功"""
        response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["username"] == "admin"

    def test_login_invalid_password(self):
        """测试登录失败（密码错误）"""
        response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrong_password"
        })
        assert response.status_code == 401

    def test_logout(self):
        """测试登出"""
        # 先登录
        client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        # 登出
        response = client.post("/api/auth/logout")
        assert response.status_code == 200

    def test_get_me_unauthenticated(self):
        """测试未登录获取用户信息"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestProjectAPI:
    """项目 API 测试"""

    def setup_method(self):
        """每个测试前登录"""
        client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

    def test_create_project(self):
        """测试创建项目"""
        response = client.post("/api/projects/", json={
            "name": "Test Project",
            "description": "Test Description",
            "type": "python"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["type"] == "python"

    def test_get_projects(self):
        """测试获取项目列表"""
        response = client.get("/api/projects/")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data

    def test_get_project_detail(self):
        """测试获取项目详情"""
        # 先创建项目
        create_response = client.post("/api/projects/", json={
            "name": "Test Project Detail",
            "description": "Test Description",
            "type": "java"
        })
        project_id = create_response.json()["id"]

        # 获取详情
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project Detail"

    def test_update_project(self):
        """测试更新项目"""
        # 先创建项目
        create_response = client.post("/api/projects/", json={
            "name": "Original Name",
            "description": "Original Description",
            "type": "python"
        })
        project_id = create_response.json()["id"]

        # 更新项目
        response = client.put(f"/api/projects/{project_id}", json={
            "name": "Updated Name",
            "description": "Updated Description",
            "type": "java"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_delete_project(self):
        """测试删除项目"""
        # 先创建项目
        create_response = client.post("/api/projects/", json={
            "name": "Project to Delete",
            "description": "Test Description",
            "type": "python"
        })
        project_id = create_response.json()["id"]

        # 删除项目
        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 200

        # 验证项目不存在
        get_response = client.get(f"/api/projects/{project_id}")
        assert get_response.status_code == 404


class TestConfigAPI:
    """配置 API 测试"""

    def setup_method(self):
        """每个测试前登录"""
        client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

    def test_set_config(self):
        """测试设置配置"""
        # 先创建项目
        create_response = client.post("/api/projects/", json={
            "name": "Config Test Project",
            "description": "Test Description",
            "type": "python"
        })
        project_id = create_response.json()["id"]

        # 设置配置
        response = client.post(f"/api/projects/{project_id}/configs/", json={
            "env_type": "dev",
            "config_key": "database_url",
            "config_value": "jdbc:mysql://localhost:3306/testdb"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["config_key"] == "database_url"

    def test_get_config(self):
        """测试获取配置"""
        # 先创建项目
        create_response = client.post("/api/projects/", json={
            "name": "Config Get Test",
            "description": "Test Description",
            "type": "python"
        })
        project_id = create_response.json()["id"]

        # 设置配置
        client.post(f"/api/projects/{project_id}/configs/", json={
            "env_type": "dev",
            "config_key": "database_url",
            "config_value": "jdbc:mysql://localhost:3306/testdb"
        })

        # 获取配置
        response = client.get(f"/api/projects/{project_id}/configs/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["configs"]) > 0

    def test_resolve_config(self):
        """测试配置解析"""
        # 先创建项目
        create_response = client.post("/api/projects/", json={
            "name": "Config Resolve Test",
            "description": "Test Description",
            "type": "python"
        })
        project_id = create_response.json()["id"]

        # 设置配置
        client.post(f"/api/projects/{project_id}/configs/", json={
            "env_type": "dev",
            "config_key": "database_url",
            "config_value": "jdbc:mysql://localhost:3306/testdb"
        })

        # 解析配置
        response = client.post(f"/api/projects/{project_id}/configs/dev/resolve", json={
            "keys": ["database_url"]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["database_url"] == "jdbc:mysql://localhost:3306/testdb"


class TestReviewAPI:
    """审核 API 测试"""

    def setup_method(self):
        """每个测试前登录"""
        client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

    def test_submit_review(self):
        """测试提交审核"""
        response = client.post("/api/reviews/", json={
            "document_id": 1,
            "action": "promote_to_public",
            "content": "Test content for review"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"

    def test_get_reviews(self):
        """测试获取审核列表"""
        # 先提交一个审核
        client.post("/api/reviews/", json={
            "document_id": 2,
            "action": "update_public",
            "content": "Test content for review 2"
        })

        # 获取审核列表
        response = client.get("/api/reviews/?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data["reviews"]) > 0

    def test_approve_review(self):
        """测试审核通过"""
        # 先提交一个审核
        submit_response = client.post("/api/reviews/", json={
            "document_id": 3,
            "action": "promote_to_public",
            "content": "Test content for approval"
        })
        review_id = submit_response.json()["id"]

        # 审核通过
        response = client.post(f"/api/reviews/{review_id}/approve", json={
            "comment": "Approved by admin"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    def test_reject_review(self):
        """测试审核拒绝"""
        # 先提交一个审核
        submit_response = client.post("/api/reviews/", json={
            "document_id": 4,
            "action": "promote_to_public",
            "content": "Test content for rejection"
        })
        review_id = submit_response.json()["id"]

        # 审核拒绝
        response = client.post(f"/api/reviews/{review_id}/reject", json={
            "reason": "Does not meet requirements"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
