import pytest

from app.services.quality_gate import _extra_checks


def test_no_issues_clean_content():
    issues = _extra_checks("Hello World\n", "knowledge")
    assert len(issues) == 0


def test_line_too_long():
    content = "x" * 150 + "\n"
    issues = _extra_checks(content, "knowledge")
    line_issues = [i for i in issues if i["rule"] == "line-length"]
    assert len(line_issues) == 1


def test_trailing_whitespace():
    content = "hello   \n"
    issues = _extra_checks(content, "knowledge")
    ws_issues = [i for i in issues if i["rule"] == "trailing-whitespace"]
    assert len(ws_issues) == 1


def test_missing_newline():
    content = "hello"
    issues = _extra_checks(content, "knowledge")
    nl_issues = [i for i in issues if i["rule"] == "missing-newline"]
    assert len(nl_issues) == 1


def test_hardcoded_password():
    content = 'password = "secret123"\n'
    issues = _extra_checks(content, "knowledge")
    sec_issues = [i for i in issues if i["rule"] == "security"]
    assert len(sec_issues) >= 1
    assert sec_issues[0]["severity"] == "critical"


def test_hardcoded_api_key():
    content = 'api_key = "sk-abc123"\n'
    issues = _extra_checks(content, "knowledge")
    sec_issues = [i for i in issues if i["rule"] == "security"]
    assert len(sec_issues) >= 1


def test_rule_missing_severity():
    content = "# 编码规范\n必须使用4空格\n"
    issues = _extra_checks(content, "rule")
    sev_issues = [i for i in issues if i["rule"] == "rule-missing-severity"]
    assert len(sev_issues) == 1
    assert sev_issues[0]["severity"] == "error"


def test_rule_has_severity():
    content = "severity: high\n必须使用4空格\n"
    issues = _extra_checks(content, "rule")
    sev_issues = [i for i in issues if i["rule"] == "rule-missing-severity"]
    assert len(sev_issues) == 0


def test_skill_missing_content():
    content = "# My Skill\nSome description\n"
    issues = _extra_checks(content, "skill")
    sk_issues = [i for i in issues if i["rule"] == "skill-missing-content"]
    assert len(sk_issues) == 1


def test_skill_has_instruction():
    content = "instruction: review code\ncontent: check for bugs\n"
    issues = _extra_checks(content, "skill")
    sk_issues = [i for i in issues if i["rule"] == "skill-missing-content"]
    assert len(sk_issues) == 0


def test_eval_detected():
    content = 'eval("1+1")\n'
    issues = _extra_checks(content, "knowledge")
    sec_issues = [i for i in issues if i["rule"] == "security" and "eval()" in i["message"]]
    assert len(sec_issues) >= 1
