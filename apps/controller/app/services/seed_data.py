"""
Seed Data - 初始化系统模板数据
"""
import json
import logging
from sqlalchemy import select, and_

from app.db.database import async_session_factory
from app.modules.agents.models import Agent
from app.modules.workflows.models import Workflow, WorkflowStep
from app.modules.knowledge.models import DocumentTemplate

logger = logging.getLogger(__name__)

AGENT_TEMPLATES = [
    {"name": "全栈工程师", "role": "fullstack", "instructions": "你精通 Python(FastAPI) 和 JS(Vue3/React)。遵循 PEP8，数据库查询必须参数化，错误处理必须完整。", "scope": "global", "is_template": True},
    {"name": "后端工程师", "role": "backend", "instructions": "你精通 Python/Go。禁止使用 eval/exec，密码必须 bcrypt 加密，敏感信息必须环境变量注入。", "scope": "global", "is_template": True},
    {"name": "前端工程师", "role": "frontend", "instructions": "你精通 Vue3/React/TypeScript。组件必须单文件，使用 Composition API，TypeScript 严格模式。", "scope": "global", "is_template": True},
    {"name": "DevOps 工程师", "role": "devops", "instructions": "你精通 Docker/K8s/CI/CD。镜像必须多阶段构建，生产环境必须灰度发布，必须有回滚方案。", "scope": "global", "is_template": True},
    {"name": "代码审查员", "role": "reviewer", "instructions": "审查代码正确性、安全漏洞、性能问题、风格一致性。每次输出问题列表、改进建议、是否通过。", "scope": "global", "is_template": True},
]

WORKFLOW_TEMPLATES = [
    {"name": "全栈开发流程", "description": "需求到部署的完整流程", "category": "development", "trigger": "manual", "is_template": True, "steps": [
        {"name": "需求分析", "order": 0, "on_fail": {"action": "stop"}},
        {"name": "数据库设计", "order": 1, "on_fail": {"action": "stop"}},
        {"name": "后端开发", "order": 2, "timeout": 600, "on_fail": {"action": "stop"}},
        {"name": "前端开发", "order": 3, "timeout": 600, "on_fail": {"action": "stop"}},
        {"name": "集成测试", "order": 4, "on_fail": {"action": "retry", "retry_count": 2}},
        {"name": "审查", "order": 5, "conditions": {"require_approval": True}, "on_fail": {"action": "stop"}},
        {"name": "部署", "order": 6, "on_fail": {"action": "rollback", "rollback_step": 5}},
    ]},
    {"name": "部署上线", "description": "生产部署含灰度", "category": "deployment", "trigger": "manual", "is_template": True, "steps": [
        {"name": "构建镜像", "order": 0, "timeout": 300, "on_fail": {"action": "stop"}},
        {"name": "安全扫描", "order": 1, "on_fail": {"action": "stop"}},
        {"name": "灰度发布", "order": 2, "conditions": {"require_approval": True}, "on_fail": {"action": "rollback", "rollback_step": 0}},
        {"name": "全量发布", "order": 3, "on_fail": {"action": "rollback", "rollback_step": 2}},
    ]},
]

DOCUMENT_TEMPLATES = [
    {"name": "PRD 需求文档", "category": "prd", "description": "产品需求文档模板", "content": "# PRD: {{项目名称}}\n\n## 1. 背景\n{{背景}}\n\n## 2. 用户故事\n作为{{角色}}，我想要{{功能}}\n\n## 3. 功能需求\n- {{需求}}\n\n## 4. 验收标准\n- {{标准}}"},
    {"name": "架构决策记录 ADR", "category": "arch", "description": "架构决策记录", "content": "# ADR: {{决策标题}}\n\n## 上下文\n{{背景}}\n\n## 决策\n采用{{方案}}\n\n## 备选\n- {{备选A}}\n- {{备选B}}\n\n## 理由\n{{理由}}"},
    {"name": "Sprint 计划", "category": "plan", "description": "迭代计划", "content": "# Sprint {{编号}}\n\n周期: {{开始}} → {{结束}}\n\n## 目标\n{{目标}}\n\n## 任务\n| 优先级 | 任务 | 负责人 |\n|-------|------|-------|\n| P0 | {{任务1}} | {{负责人1}} |"},
]


async def seed_templates():
    try:
        async with async_session_factory() as db:
            # Agent templates
            existing_agents = set()
            result = await db.execute(select(Agent.name).where(Agent.is_template == True))
            for row in result.all():
                existing_agents.add(row[0])

            for tpl in AGENT_TEMPLATES:
                if tpl["name"] not in existing_agents:
                    db.add(Agent(**tpl))

            # Workflow templates
            existing_wfs = set()
            result = await db.execute(select(Workflow.name).where(Workflow.is_template == True))
            for row in result.all():
                existing_wfs.add(row[0])

            for tpl in WORKFLOW_TEMPLATES:
                if tpl["name"] not in existing_wfs:
                    steps = tpl.pop("steps", [])
                    wf = Workflow(**tpl)
                    db.add(wf)
                    await db.flush()
                    for s in steps:
                        step_data = dict(s)
                        for k in ['on_fail', 'on_success', 'conditions', 'input_mapping', 'output_mapping', 'skill_ids', 'rule_ids']:
                            if k in step_data and isinstance(step_data[k], (dict, list)):
                                step_data[k] = json.dumps(step_data[k])
                        db.add(WorkflowStep(workflow_id=wf.id, **step_data))
                    tpl["steps"] = steps

            # Document templates
            existing_docs = set()
            result = await db.execute(select(DocumentTemplate.name).where(DocumentTemplate.scope == "global"))
            for row in result.all():
                existing_docs.add(row[0])

            for tpl in DOCUMENT_TEMPLATES:
                if tpl["name"] not in existing_docs:
                    db.add(DocumentTemplate(
                        name=tpl["name"], category=tpl["category"],
                        description=tpl.get("description", ""),
                        content=tpl["content"], scope="global"
                    ))

            await db.commit()
            logger.info(f"Seed data initialized")
    except Exception as e:
        logger.warning(f"Seed data failed: {e}")