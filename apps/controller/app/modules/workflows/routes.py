"""
Workflows Module Routes
流程引擎 API 路由
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.database import get_db, async_session_factory
from app.modules.workflows.models import Workflow, WorkflowStep, WorkflowExecution, WorkflowExecutionStep
from app.core.permissions import require_permissions
from app.core.utils import get_current_user_id
from app.api.auth import get_current_user

router = APIRouter()


class StepCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    order: int = 0
    agent_id: Optional[str] = None
    skill_ids: List[str] = Field(default_factory=list)
    rule_ids: List[str] = Field(default_factory=list)
    conditions: Optional[dict] = Field(default_factory=dict)
    input_mapping: Optional[dict] = Field(default_factory=dict)
    output_mapping: Optional[dict] = Field(default_factory=dict)
    timeout: int = 300
    on_success: Optional[dict] = Field(default_factory=dict)
    on_fail: Optional[dict] = Field(default_factory=dict)


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = "development"
    trigger: str = "manual"
    trigger_config: Optional[dict] = Field(default_factory=dict)
    variables: List[dict] = Field(default_factory=list)
    steps: List[StepCreate] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    trigger: Optional[str] = None
    trigger_config: Optional[dict] = None
    variables: Optional[List[dict]] = None
    is_active: Optional[bool] = None


# ==================== Workflow CRUD ====================

@router.get("/list")
async def list_workflows(
    category: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    is_template: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Workflow).where(Workflow.deleted_at.is_(None))
    if category:
        query = query.where(Workflow.category == category)
    if project_id:
        query = query.where(Workflow.project_id == project_id)
    else:
        query = query.where(Workflow.project_id.is_(None))
    if is_template is not None:
        query = query.where(Workflow.is_template == is_template)
    if search:
        p = f"%{search}%"
        query = query.where(or_(Workflow.name.ilike(p), Workflow.description.ilike(p)))
    total_q = select(func.count()).select_from(query.subquery())
    total_r = await db.execute(total_q)
    total = total_r.scalar() or 0
    query = query.order_by(desc(Workflow.updated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    workflows = result.scalars().all()
    return {"items": [w.to_dict() for w in workflows], "total": total}


@router.post("/create")
async def create_workflow(
    data: WorkflowCreate,
    project_id: Optional[int] = Query(None),
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    wf = Workflow(
        name=data.name, description=data.description, category=data.category,
        trigger=data.trigger, trigger_config=json.dumps(data.trigger_config),
        variables=json.dumps(data.variables),
        project_id=project_id, user_id=user_id
    )
    db.add(wf)
    await db.flush()
    for i, s in enumerate(data.steps or []):
        step = WorkflowStep(
            workflow_id=wf.id, name=s.name, order=s.order or i,
            agent_id=s.agent_id, skill_ids=json.dumps(s.skill_ids),
            rule_ids=json.dumps(s.rule_ids),
            conditions=json.dumps(s.conditions), input_mapping=json.dumps(s.input_mapping),
            output_mapping=json.dumps(s.output_mapping), timeout=s.timeout,
            on_success=json.dumps(s.on_success), on_fail=json.dumps(s.on_fail)
        )
        db.add(step)
    await db.commit()
    await db.refresh(wf, ['steps'])
    return wf.to_dict(include_steps=True)


@router.get("/executions/list")
async def list_executions(
    workflow_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(WorkflowExecution)
    if workflow_id:
        query = query.where(WorkflowExecution.workflow_id == workflow_id)
    if status:
        query = query.where(WorkflowExecution.status == status)
    query = query.order_by(desc(WorkflowExecution.created_at)).limit(limit)
    result = await db.execute(query)
    executions = result.scalars().all()
    return {"items": [e.to_dict() for e in executions]}


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution.to_dict()


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    execution.status = "cancelled"
    execution.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True}


# ==================== Templates ====================

@router.get("/templates/list")
async def list_templates(
    category: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import text as sa_text
    sql = "SELECT id, name, description, category, trigger, project_id, user_id, is_active, is_template, version, created_at, updated_at FROM aidp_workflows WHERE deleted_at IS NULL AND is_template = true"
    params = {}
    if category:
        sql += " AND category = :cat"
        params["cat"] = category
    sql += " ORDER BY category, name"
    result = await db.execute(sa_text(sql), params)
    rows = result.fetchall()
    items = []
    for row in rows:
        items.append({
            "id": row[0], "name": row[1], "description": row[2], "category": row[3],
            "trigger": row[4], "trigger_config": {}, "variables": [],
            "project_id": row[5], "user_id": row[6],
            "is_active": row[7], "is_template": row[8], "version": row[9],
            "created_at": str(row[10]) if row[10] else None,
            "updated_at": str(row[11]) if row[11] else None,
        })
    return {"items": items}


@router.get("/stats")
async def get_workflow_stats(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    total = await db.execute(select(func.count(Workflow.id)).where(Workflow.deleted_at.is_(None)))
    by_category = await db.execute(
        select(Workflow.category, func.count(Workflow.id)).where(Workflow.deleted_at.is_(None)).group_by(Workflow.category)
    )
    active_execs = await db.execute(select(func.count(WorkflowExecution.id)).where(WorkflowExecution.status == "running"))
    return {
        "total": total.scalar() or 0,
        "by_category": {r[0]: r[1] for r in by_category.all()},
        "active_executions": active_execs.scalar() or 0
    }
@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Workflow).where(and_(Workflow.id == workflow_id, Workflow.deleted_at.is_(None))).options(selectinload(Workflow.steps))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf.to_dict(include_steps=True)


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    data: WorkflowUpdate,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Workflow).where(and_(Workflow.id == workflow_id, Workflow.deleted_at.is_(None))).options(selectinload(Workflow.steps))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    simple = ['name', 'description', 'category', 'trigger', 'is_active']
    json_fields = {'trigger_config': data.trigger_config, 'variables': data.variables}
    for f in simple:
        v = getattr(data, f)
        if v is not None:
            setattr(wf, f, v)
    for f, v in json_fields.items():
        if v is not None:
            setattr(wf, f, json.dumps(v))
    await db.commit()
    await db.refresh(wf)
    return wf.to_dict(include_steps=True)


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Workflow).where(and_(Workflow.id == workflow_id, Workflow.deleted_at.is_(None))).options(selectinload(Workflow.steps))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    wf.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True}


# ==================== Step Management ====================

@router.post("/{workflow_id}/steps")
async def add_step(
    workflow_id: str,
    data: StepCreate,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workflow not found")
    step = WorkflowStep(
        workflow_id=workflow_id, name=data.name, order=data.order,
        agent_id=data.agent_id, skill_ids=json.dumps(data.skill_ids),
        rule_ids=json.dumps(data.rule_ids), conditions=json.dumps(data.conditions),
        input_mapping=json.dumps(data.input_mapping),
        output_mapping=json.dumps(data.output_mapping), timeout=data.timeout,
        on_success=json.dumps(data.on_success), on_fail=json.dumps(data.on_fail)
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step.to_dict()


@router.put("/{workflow_id}/steps/{step_id}")
async def update_step(
    workflow_id: str, step_id: str,
    data: StepCreate,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(WorkflowStep).where(and_(WorkflowStep.id == step_id, WorkflowStep.workflow_id == workflow_id)))
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    for f in ['name', 'order', 'agent_id', 'timeout']:
        v = getattr(data, f)
        if v is not None:
            setattr(step, f, v)
    for f in ['skill_ids', 'rule_ids', 'conditions', 'input_mapping', 'output_mapping', 'on_success', 'on_fail']:
        v = getattr(data, f)
        if v is not None:
            setattr(step, f, json.dumps(v))
    await db.commit()
    await db.refresh(step)
    return step.to_dict()


@router.delete("/{workflow_id}/steps/{step_id}")
async def delete_step(
    workflow_id: str, step_id: str,
    user=require_permissions("skills:write:personal"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(WorkflowStep).where(and_(WorkflowStep.id == step_id, WorkflowStep.workflow_id == workflow_id)))
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    await db.delete(step)
    await db.commit()
    return {"success": True}


# ==================== Execute ====================

@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
variables: Optional[str] = Query(None, description="JSON string of variables"),
    db: AsyncSession = Depends(get_db)
):
    parsed_vars = json.loads(variables) if variables else {}
    result = await db.execute(
        select(Workflow).where(and_(Workflow.id == workflow_id, Workflow.deleted_at.is_(None)))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    execution = WorkflowExecution(
        workflow_id=workflow_id, status="running",
        variables=json.dumps(parsed_vars), started_at=datetime.now(timezone.utc)
    )
    db.add(execution)
    await db.flush()

    steps = await db.execute(
        select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.order)
    )
    steps_list = steps.scalars().all()

    for step in steps_list:
        es = WorkflowExecutionStep(
            execution_id=execution.id, step_id=step.id,
            step_name=step.name, step_order=step.order, status="completed"
        )
        db.add(es)

    execution.status = "completed"
    execution.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(execution)
    return execution.to_dict()


# ==================== Execution History ====================
