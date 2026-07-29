import pytest

from app.services.categorizer import recommend_tags


def test_architecture_tags():
    result = recommend_tags("微服务架构设计文档\ndocker部署方案", "arch.md", "knowledge")
    tags = result["tags"]
    assert "knowledge" in tags
    assert "architecture" in tags or "devops" in tags


def test_api_category():
    result = recommend_tags("API接口文档\n登录接口", "login.md", "knowledge")
    assert result["category"] == "api/overview"


def test_sql_category():
    result = recommend_tags("CREATE TABLE users (\nid INT", "schema.sql", "knowledge")
    assert result["category"] == "database/schema"


def test_rule_severity_high():
    content = "# 安全规范\nseverity: critical\n必须使用HTTPS\n禁止明文密码"
    result = recommend_tags(content, "security.md", "rule")
    assert result["severity"] == "critical"


def test_rule_severity_not_applicable():
    result = recommend_tags("# 普通文档", "doc.md", "knowledge")
    assert result["severity"] is None


def test_erp_category():
    text = "ERP采购销售流程\n采购入库单状态机"
    result = recommend_tags(text, "procurement.md", "knowledge")
    assert result["category"] == "erp/overview"


def test_plan_tags():
    result = recommend_tags("开发蓝图", "plan.md", "plan")
    assert "plan" in result["tags"]


def test_no_duplicate_tags():
    result = recommend_tags("python python python", "script.py", "knowledge")
    count = result["tags"].count("python")
    assert count <= 1
