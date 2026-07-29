import pytest

from app.services.classifier import classify_content


def test_classify_skill():
    content = "instruction: review code\ncontent: check for bugs"
    result = classify_content(content, "review.md")
    assert result["type"] == "skill"
    assert result["confidence"] == "high"


def test_classify_rule():
    content = "# Coding Rules\nseverity: high\n必须使用4空格缩进\n禁止使用tab"
    result = classify_content(content, "rules.md")
    assert result["type"] == "rule"
    assert result["confidence"] == "high"


def test_classify_adr():
    result = classify_content("# ADR-001\nSome decision", "ADR-001-db-design.md")
    assert result["type"] == "knowledge"
    assert result["confidence"] == "high"


def test_classify_plan():
    result = classify_content("# Development Plan", "erp-master-plan.md")
    assert result["type"] == "plan"
    assert result["confidence"] == "medium"


def test_classify_architecture():
    result = classify_content("# 系统架构总览\n系统采用微服务架构", "architecture.md")
    assert result["type"] == "knowledge"


def test_classify_generic_markdown():
    result = classify_content("# Hello World\nSome content", "readme.md")
    assert result["type"] == "knowledge"
    assert result["title"] == "Hello World"


def test_classify_empty_content():
    result = classify_content("", "empty.md")
    assert result["type"] == "knowledge"
    assert result["confidence"] == "low"


def test_title_extraction():
    result = classify_content("# My Document Title\n\nbody", "file.md")
    assert result["title"] == "My Document Title"


def test_title_fallback_filename():
    result = classify_content("plain text no heading", "my-doc.md")
    assert result["title"] == "My Doc"
