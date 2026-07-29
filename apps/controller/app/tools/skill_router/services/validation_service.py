import re
from typing import Optional, List, Dict, Any
from datetime import datetime

# P0: 敏感数据泄露检测模式
SENSITIVE_PATTERNS = [
    r"password.*=\s*['\"][^'\"]+['\"]",
    r"api_key.*=\s*['\"][^'\"]+['\"]",
    r"sk-[a-zA-Z0-9]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Email addresses
    r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b",  # Credit card numbers
]

# P0: 禁止执行的危险操作模式
DANGEROUS_OPERATIONS = [
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__\s*\(",
    r"subprocess\.call\s*\(",
    r"os\.system\s*\(",
    r"rm\s+-rf",
    r"DELETE\s+FROM",
    r"DROP\s+TABLE",
]


def validate_params(params: dict, schema: dict) -> List[Dict[str, Any]]:
    """
    P0: 参数校验增强版
    支持必填项、类型检查、范围检查、格式校验
    """
    errors = []
    props = schema.get("properties", {}) if schema else {}
    required = schema.get("required", []) if schema else []
    
    # 1. 必填项检查
    for field in required:
        if field not in params or params[field] is None or params[field] == "":
            errors.append({
                "field": field, 
                "error": "required", 
                "message": f"'{field}' is required",
                "severity": "high"
            })
    
    # 2. 类型检查
    for field, value in params.items():
        prop = props.get(field)
        if not prop:
            continue
        
        expected_type = prop.get("type", "string")
        
        # Integer检查
        if expected_type == "integer":
            try:
                int(value)
            except (ValueError, TypeError):
                errors.append({
                    "field": field,
                    "error": "type_mismatch",
                    "message": f"'{field}' should be integer, got {type(value).__name__}",
                    "severity": "medium"
                })
        
        # Boolean检查
        elif expected_type == "boolean" and not isinstance(value, bool):
            if str(value).lower() not in ("true", "false", "1", "0"):
                errors.append({
                    "field": field,
                    "error": "type_mismatch",
                    "message": f"'{field}' should be boolean",
                    "severity": "medium"
                })
        
        # String格式检查（新增）
        elif expected_type == "string":
            format_type = prop.get("format")
            if format_type == "email" and value:
                if not re.match(r"[^@]+@[^@]+\.[^@]+", str(value)):
                    errors.append({
                        "field": field,
                        "error": "format_invalid",
                        "message": f"'{field}' should be valid email format",
                        "severity": "medium"
                    })
            elif format_type == "date" and value:
                try:
                    datetime.strptime(str(value), "%Y-%m-%d")
                except ValueError:
                    errors.append({
                        "field": field,
                        "error": "format_invalid",
                        "message": f"'{field}' should be valid date format (YYYY-MM-DD)",
                        "severity": "medium"
                    })
        
        # Range检查（新增）
        if prop.get("minimum") is not None:
            try:
                val = float(value)
                if val < prop["minimum"]:
                    errors.append({
                        "field": field,
                        "error": "range_invalid",
                        "message": f"'{field}' should be >= {prop['minimum']}",
                        "severity": "medium"
                    })
            except (ValueError, TypeError):
                pass
        
        if prop.get("maximum") is not None:
            try:
                val = float(value)
                if val > prop["maximum"]:
                    errors.append({
                        "field": field,
                        "error": "range_invalid",
                        "message": f"'{field}' should be <= {prop['maximum']}",
                        "severity": "medium"
                    })
            except (ValueError, TypeError):
                pass
    
    return errors


def validate_output(content: str, skill_tags: Optional[list] = None) -> List[Dict[str, Any]]:
    """
    P0: 输出内容校验增强版
    检测敏感数据泄露、危险操作、编造内容
    """
    warnings = []
    
    # 1. 敏感数据泄露检测
    for pat in SENSITIVE_PATTERNS:
        matches = re.findall(pat, content, re.IGNORECASE)
        for m in matches:
            warnings.append({
                "pattern": pat[:30], 
                "match": m[:50], 
                "severity": "high",
                "type": "sensitive_data_leak",
                "message": "Potential sensitive data detected in output"
            })
    
    # 2. 危险操作检测（新增）
    for pat in DANGEROUS_OPERATIONS:
        matches = re.findall(pat, content, re.IGNORECASE)
        for m in matches:
            warnings.append({
                "pattern": pat[:30],
                "match": m[:50],
                "severity": "critical",
                "type": "dangerous_operation",
                "message": "Dangerous operation pattern detected"
            })
    
    # 3. 业务规则检测
    if skill_tags and any(t.lower() in ("financial", "payment", "accounting", "billing") for t in skill_tags):
        warnings.append({
            "pattern": "financial_skill", 
            "match": "", 
            "severity": "medium",
            "type": "business_rule",
            "message": "Output from financial skill should be reviewed before use"
        })
    
    # 4. 编造内容检测（新增）
    # 检测看起来像数据但实际上是占位符的内容
    placeholder_patterns = [
        r"\bxxx\b",
        r"\btest\b",
        r"\bplaceholder\b",
        r"\bsample\b",
        r"\bexample\b",
        r"\bTODO\b",
        r"\bFIXME\b",
    ]
    for pat in placeholder_patterns:
        if re.search(pat, content, re.IGNORECASE):
            warnings.append({
                "pattern": pat,
                "match": "",
                "severity": "medium",
                "type": "placeholder_content",
                "message": f"Potential placeholder/test content detected"
            })
    
    return warnings


def validate_resolve_result(result: dict) -> dict:
    """
    P0: resolve结果后置校验增强版
    综合校验参数、输出、权限、审批
    """
    validations = {
        "param_errors": [],
        "output_warnings": [],
        "sensitive_skills": [],
        "dangerous_operations": [],
        "business_rules": [],
        "placeholder_content": [],
        "approval_required": False,
        "blocked": False,
        "dynamic_rules": []
    }
    
    for s in result.get("skills", []):
        # 1. 敏感技能标记
        if s.get("sensitive"):
            validations["sensitive_skills"].append({
                "id": s["id"], 
                "name": s["name"], 
                "message": "Sensitive skill requires secondary confirmation",
                "severity": "high"
            })
            validations["approval_required"] = True
        
        # 2. 输出内容校验
        if s.get("content"):
            output_warnings = validate_output(s["content"], s.get("tags"))
            
            # 分类存储不同类型的警告
            for warning in output_warnings:
                warning_type = warning.get("type", "unknown")
                if warning_type == "sensitive_data_leak":
                    validations["output_warnings"].append({**warning, "skill_id": s["id"]})
                elif warning_type == "dangerous_operation":
                    validations["dangerous_operations"].append({**warning, "skill_id": s["id"]})
                    validations["blocked"] = True  # 发现危险操作则阻止执行
                elif warning_type == "business_rule":
                    validations["business_rules"].append({**warning, "skill_id": s["id"]})
                elif warning_type == "placeholder_content":
                    validations["placeholder_content"].append({**warning, "skill_id": s["id"]})
        
        # 3. 权限校验（新增）
        if s.get("allowed_roles"):
            # 这里应该检查当前用户角色是否在allowed_roles中
            # 由于此时没有用户信息，只记录需要权限校验
            validations["business_rules"].append({
                "skill_id": s["id"],
                "skill_name": s["name"],
                "type": "role_permission",
                "message": f"Skill '{s['name']}' requires role permission check",
                "severity": "medium"
            })
        
        # 4. 版本状态校验（新增）
        review_status = s.get("review_status", "pending")
        if review_status != "approved":
            validations["business_rules"].append({
                "skill_id": s["id"],
                "skill_name": s["name"],
                "type": "review_status",
                "message": f"Skill '{s['name']}' is not approved (status: {review_status})",
                "severity": "medium"
            })
    
    # 5. 生成动态规则（新增）
    # 如果发现了问题，生成动态规则供LLM二次修正
    if validations["dangerous_operations"]:
        validations["dynamic_rules"].append("BLOCK: Dangerous operations detected. Cannot execute.")
    
    if validations["approval_required"]:
        validations["dynamic_rules"].append("APPROVAL: One or more skills require approval before execution.")
    
    if validations["placeholder_content"]:
        validations["dynamic_rules"].append("WARNING: Placeholder content detected. Verify output before use.")
    
    if validations["business_rules"]:
        validations["dynamic_rules"].append("CHECK: Business rules require validation before execution.")
    
    # 6. 综合判断是否可以执行
    validations["can_execute"] = not validations["blocked"] and not validations["approval_required"]
    
    result["validation"] = validations
    return result


def validate_skill_execution(skill_data: dict, params: dict, user_role: Optional[str] = None) -> dict:
    """
    P0: 技能执行前的最终校验
    集成参数校验、权限校验、业务规则校验
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "approval_required": False,
        "dynamic_rules": []
    }
    
    # 1. 参数校验
    exec_config = skill_data.get("exec_config", {})
    param_schema = exec_config.get("params", {}).get("schema", {})
    if param_schema:
        param_errors = validate_params(params, param_schema)
        validation_result["errors"].extend(param_errors)
    
    # 2. 权限校验
    allowed_roles = skill_data.get("allowed_roles")
    if allowed_roles and user_role:
        if user_role not in allowed_roles:
            validation_result["errors"].append({
                "field": "permission",
                "error": "role_denied",
                "message": f"User role '{user_role}' is not allowed to execute this skill",
                "severity": "critical"
            })
            validation_result["valid"] = False
    
    # 3. 敏感技能审批校验
    if skill_data.get("sensitive"):
        validation_result["approval_required"] = True
        validation_result["warnings"].append({
            "field": "sensitivity",
            "message": "This skill requires approval before execution",
            "severity": "high"
        })
    
    # 4. 审查状态校验
    review_status = skill_data.get("review_status", "pending")
    if review_status != "approved":
        validation_result["warnings"].append({
            "field": "review_status",
            "message": f"Skill review status is '{review_status}', not approved",
            "severity": "medium"
        })
    
    # 5. 最终判定
    if validation_result["errors"]:
        validation_result["valid"] = False
        validation_result["dynamic_rules"].append("BLOCK: Validation errors detected")
    
    if validation_result["approval_required"]:
        validation_result["dynamic_rules"].append("APPROVAL: Manual approval required")
    
    return validation_result
