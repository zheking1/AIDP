"""
AIDP Agent Instructions 5-Stage Context Pipeline

Stage 0: Load Agent Instructions
Stage 1: Intent Analysis
Stage 2: Staged Retrieval (Memory -> Knowledge -> Asset -> Code)
Stage 3: Skill Matching (via SkillRouter)
Stage 4: Context Assembly
"""

import time
import uuid
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.instructions import AgentInstruction
from app.services.tool_invoker import ToolInvoker
from app.services.context_cache import ContextCache
from app.services.context_assembly import ContextAssembler
from app.services.tool_retry import ToolRetryManager, RetryConfig, RetryStrategy, FallbackManager

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Context object passed through all pipeline stages"""
    trace_id: str
    project_id: str
    task: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Stage 0: Instructions
    instructions: dict = field(default_factory=dict)
    
    # Stage 1: Intent
    intent: dict = field(default_factory=dict)
    
    # Stage 2: Retrieved Data
    memories: list = field(default_factory=list)
    knowledge: list = field(default_factory=list)
    assets: list = field(default_factory=list)
    code_context: list = field(default_factory=list)
    
    # Stage 3: Skills
    skills: list = field(default_factory=list)
    rules: list = field(default_factory=list)
    
    # Stage 4: Final Assembly
    assembled_context: dict = field(default_factory=dict)
    
    # Metadata
    stage_timings: dict = field(default_factory=dict)
    token_estimate: int = 0


class ContextPipeline:
    """5-Stage Context Pipeline for AIDP"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tool_invoker = ToolInvoker()
        self.cache = ContextCache(ttl_seconds=300)
        self.assembler = ContextAssembler(max_tokens=8000)
        self.retry_manager = ToolRetryManager(RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL
        ))
        self.fallback_manager = FallbackManager()
    
    async def execute(self, task: str, project_id: str = "0", 
                     user_id: Optional[str] = None,
                     session_id: Optional[str] = None,
                     hint_tags: list = None) -> PipelineContext:
        """Execute full 5-stage pipeline"""
        
        trace_id = str(uuid.uuid4())[:8]
        ctx = PipelineContext(
            trace_id=trace_id,
            project_id=project_id,
            task=task,
            user_id=user_id,
            session_id=session_id
        )
        
        print(f"[{trace_id}] Starting 5-Stage Pipeline for task: {task[:50]}...")
        
        try:
            # Stage 0: Load Instructions
            await self._stage_0_load_instructions(ctx)
            
            # Stage 1: Intent Analysis
            await self._stage_1_intent_analysis(ctx)
            
            # Stage 2: Staged Retrieval
            await self._stage_2_staged_retrieval(ctx, hint_tags)
            
            # Stage 3: Skill Matching
            await self._stage_3_skill_matching(ctx)
            
            # Stage 4: Context Assembly
            await self._stage_4_assembly(ctx)
            
            print(f"[{trace_id}] Pipeline completed in {sum(ctx.stage_timings.values()):.0f}ms")
            return ctx
            
        except Exception as e:
            print(f"[{trace_id}] Pipeline error: {e}")
            raise
    
    async def _stage_0_load_instructions(self, ctx: PipelineContext):
        """Stage 0: 根据意图领域匹配 Agent, 加载对应指令"""
        start = time.time()

        # 尝试按 domain 匹配项目 Agent
        domains = ctx.intent.get("domains", []) if ctx.intent else []
        try:
            from app.modules.agents.models import Agent as AgentModel
            import json as _json

            agent_result = await self.db.execute(
                select(AgentModel).where(
                    and_(
                        AgentModel.project_id == int(ctx.project_id),
                        AgentModel.is_active == True,
                        AgentModel.deleted_at.is_(None),
                    )
                )
            )
            agents = agent_result.scalars().all()

            best, best_score = None, 0
            for a in agents:
                agent_domains = _json.loads(a.domain_tags) if a.domain_tags else []
                score = len(set(agent_domains) & set(domains))
                if score > best_score:
                    best_score, best = score, a

            if best:
                ctx.instructions = {
                    "role": best.role or "You are a helpful AI assistant.",
                    "constraints": {},
                    "rules": [r.strip() for r in (best.instructions or "").split("\n") if r.strip()],
                    "loaded_from_db": True,
                    "agent_name": best.name,
                    "agent_key": best.agent_key,
                }
                ctx.stage_timings["stage_0"] = (time.time() - start) * 1000
                print(f"[{ctx.trace_id}] Stage 0: matched agent '{best.agent_key}' (score={best_score}) ({ctx.stage_timings['stage_0']:.0f}ms)")
                return
        except Exception:
            pass

        # Fallback: 加载 project 的通用 instructions 或全局默认
        result = await self.db.execute(
            select(AgentInstruction).where(
                AgentInstruction.project_id == int(ctx.project_id),
                AgentInstruction.agent_type == "main"
            )
        )
        inst = result.scalar_one_or_none()
        
        if inst:
            ctx.instructions = {
                "role": inst.role or "You are a helpful AI assistant.",
                "constraints": inst.constraints or {},
                "rules": inst.rules or [],
                "loaded_from_db": True
            }
        else:
            # Default instructions
            ctx.instructions = {
                "role": "You are an AI programming assistant. Help users with code-related tasks.",
                "constraints": {
                    "max_tokens": 4000,
                    "response_format": "markdown"
                },
                "rules": [
                    "Always provide code examples when relevant",
                    "Explain your reasoning step by step"
                ],
                "loaded_from_db": False
            }
        
        ctx.stage_timings["stage_0"] = (time.time() - start) * 1000
        print(f"[{ctx.trace_id}] Stage 0: Loaded instructions ({ctx.stage_timings['stage_0']:.0f}ms)")
    
    async def _stage_1_intent_analysis(self, ctx: PipelineContext):
        """Stage 1: Analyze user intent using SkillRouter"""
        start = time.time()
        
        try:
            # Call SkillRouter for intent analysis
            result = await self.tool_invoker.invoke(
                "skill-router",
                "analyze_intent",
                {
                    "task": ctx.task,
                    "session_id": ctx.session_id
                }
            )
            
            if result and result.get("success"):
                ctx.intent = result.get("data", {})
            else:
                # Fallback intent analysis
                ctx.intent = self._fallback_intent_analysis(ctx.task)
                
        except Exception as e:
            print(f"[{ctx.trace_id}] Intent analysis failed: {e}")
            ctx.intent = self._fallback_intent_analysis(ctx.task)
        
        ctx.stage_timings["stage_1"] = (time.time() - start) * 1000
        print(f"[{ctx.trace_id}] Stage 1: Intent analyzed - {ctx.intent.get('intent', 'unknown')} ({ctx.stage_timings['stage_1']:.0f}ms)")
    
    def _fallback_intent_analysis(self, task: str) -> dict:
        """Simple rule-based intent analysis as fallback"""
        task_lower = task.lower()
        
        # Detect domains
        domains = []
        keywords = {
            "api": ["api", "endpoint", "route", "request", "response"],
            "database": ["database", "sql", "query", "table", "schema"],
            "frontend": ["ui", "component", "react", "vue", "html", "css"],
            "backend": ["server", "service", "controller", "middleware"],
            "devops": ["docker", "deploy", "ci/cd", "kubernetes"],
            "security": ["auth", "login", "permission", "encrypt"],
            "testing": ["test", "unittest", "e2e", "mock"]
        }
        
        for domain, words in keywords.items():
            if any(word in task_lower for word in words):
                domains.append(domain)
        
        # Detect complexity
        complexity = "simple"
        if len(task) > 200 or "and" in task_lower or "then" in task_lower:
            complexity = "compound"
        elif any(word in task_lower for word in ["implement", "create", "build", "design"]):
            complexity = "complex"
        
        return {
            "intent": domains[0] if domains else "general",
            "domains": domains,
            "complexity": complexity,
            "tags_needed": domains,
            "is_compound": complexity == "compound"
        }
    
    async def _stage_2_staged_retrieval(self, ctx: PipelineContext, hint_tags: list = None):
        """Stage 2: Retrieve context from multiple sources with cache, retry, fallback"""
        start = time.time()
        
        tags = hint_tags or ctx.intent.get("tags_needed", [])
        domains = ctx.intent.get("domains", [])
        
        cache_key = {
            "intent": ctx.intent.get("intent"),
            "tags": tags,
            "project_id": ctx.project_id,
        }
        cached = self.cache.get("stage2", cache_key)
        if cached is not None:
            ctx.memories = cached.get("memories", [])
            ctx.knowledge = cached.get("knowledge", [])
            ctx.assets = cached.get("assets", [])
            ctx.stage_timings["stage_2"] = (time.time() - start) * 1000
            total = len(ctx.memories) + len(ctx.knowledge) + len(ctx.assets)
            print(f"[{ctx.trace_id}] Stage 2: Cache hit - {total} items ({ctx.stage_timings['stage_2']:.0f}ms)")
            return
        
        async def _retrieve_memory():
            r = await self.tool_invoker.invoke("memory-tool", "memory.search", {
                "project": ctx.project_id or "",
                "query": ctx.task,
                "category": domains[0] if domains else None,
                "limit": 5,
            })
            return r.get("data", {}).get("results", []) if r and r.get("success") else []
        
        async def _retrieve_knowledge():
            r = await self.tool_invoker.invoke("knowledge-tool", "knowledge.search", {
                "query": ctx.task, "top_k": 5, "task_domains": domains,
                "project_id": ctx.project_id,
            })
            return r.get("data", {}).get("items", []) if r and r.get("success") else []
        
        async def _retrieve_asset():
            r = await self.tool_invoker.invoke("asset-tool", "search", {
                "query": ctx.task, "tags": tags, "top_k": 3,
                "project_id": ctx.project_id,
            })
            return r.get("data", {}).get("items", []) if r and r.get("success") else []
        
        results = await asyncio.gather(
            self._safe_retrieve("memory-tool", _retrieve_memory, ctx),
            self._safe_retrieve("knowledge-tool", _retrieve_knowledge, ctx),
            self._safe_retrieve("asset-tool", _retrieve_asset, ctx),
            return_exceptions=True,
        )
        
        ctx.memories = results[0] if not isinstance(results[0], Exception) else []
        ctx.knowledge = results[1] if not isinstance(results[1], Exception) else []
        ctx.assets = results[2] if not isinstance(results[2], Exception) else []
        
        cache_data = {"memories": ctx.memories, "knowledge": ctx.knowledge, "assets": ctx.assets}
        self.cache.set("stage2", cache_key, cache_data)
        
        ctx.stage_timings["stage_2"] = (time.time() - start) * 1000
        total_items = len(ctx.memories) + len(ctx.knowledge) + len(ctx.assets)
        print(f"[{ctx.trace_id}] Stage 2: Retrieved {total_items} items (M:{len(ctx.memories)} K:{len(ctx.knowledge)} A:{len(ctx.assets)}) ({ctx.stage_timings['stage_2']:.0f}ms)")
    
    async def _safe_retrieve(self, tool_name: str, func, ctx):
        try:
            return await self.retry_manager.execute_with_retry(func)
        except Exception as e:
            logger.warning("[%s] %s retrieval failed: %s", ctx.trace_id, tool_name, e)
            fallback_msg = self.fallback_manager.handle_tool_failure(tool_name, e)
            return [{"title": f"{tool_name} degraded", "content": fallback_msg, "source": f"{tool_name}_fallback"}]
    
    async def _stage_3_skill_matching(self, ctx: PipelineContext):
        """Stage 3: Match skills using SkillRouter"""
        start = time.time()
        
        try:
            result = await self.tool_invoker.invoke(
                "skill-router",
                "skill_run",
                {
                    "task": ctx.task,
                    "mode": "auto",
                    "hint_tags": ctx.intent.get("tags_needed", []),
                    "top_k": 6,
                    "session_id": ctx.session_id
                }
            )
            
            if result and result.get("success"):
                data = result.get("data", {})
                ctx.skills = data.get("skills", [])
                ctx.rules = data.get("rules", [])
                
                # Add instruction from skills
                if data.get("instructions"):
                    ctx.instructions["skill_instructions"] = data["instructions"]
                if data.get("project_instructions"):
                    ctx.instructions["project_instructions"] = data["project_instructions"]
                    
        except Exception as e:
            print(f"[{ctx.trace_id}] Skill matching failed: {e}")
            ctx.skills = []
            ctx.rules = []
        
        ctx.stage_timings["stage_3"] = (time.time() - start) * 1000
        print(f"[{ctx.trace_id}] Stage 3: Matched {len(ctx.skills)} skills, {len(ctx.rules)} rules ({ctx.stage_timings['stage_3']:.0f}ms)")
    
    async def _stage_4_assembly(self, ctx: PipelineContext):
        """Stage 4: Assemble final context package with priority/dedup/compress"""
        start = time.time()
        
        items = []
        items.append({"source": "instructions", "content": ctx.instructions.get("role", ""),
                       "relevance_score": 1.0, "metadata": {}})
        
        constraints = ctx.instructions.get("constraints", {})
        if constraints:
            items.append({"source": "instructions", "content": "\n".join(
                [f"{k}: {v}" for k, v in constraints.items()]),
                "relevance_score": 0.9, "metadata": {}})
        
        rules = ctx.instructions.get("rules", [])
        if rules:
            items.append({"source": "instructions", "content": "\n".join([f"- {r}" for r in rules]),
                          "relevance_score": 0.8, "metadata": {}})
        
        if ctx.instructions.get("project_instructions"):
            items.append({"source": "instructions", "content": ctx.instructions["project_instructions"],
                          "relevance_score": 0.7, "metadata": {}})
        
        for m in ctx.memories[:3]:
            items.append({"source": "memory", "content": f"{m.get('title', '')}\n{m.get('content', '')[:500]}",
                          "relevance_score": 0.6, "metadata": m})
        for k in ctx.knowledge[:3]:
            items.append({"source": "knowledge", "content": f"{k.get('title', '')}\n{k.get('content', '')[:500]}",
                          "relevance_score": 0.6, "metadata": k})
        for a in ctx.assets:
            items.append({"source": "asset", "content": f"{a.get('name', '')}: {a.get('description', '')}",
                          "relevance_score": 0.4, "metadata": a})
        for s in ctx.skills[:4]:
            items.append({"source": "skill", "content": f"{s.get('name', '')}\n{s.get('content', '')[:800]}",
                          "relevance_score": 0.5, "metadata": s})
        
        assembled = self.assembler.assemble(items)
        
        ctx.token_estimate = assembled["total_tokens"]
        
        ctx.assembled_context = {
            "system_prompt": assembled["context"],
            "user_message": ctx.task,
            "compression_ratio": assembled["compression_ratio"],
            "metadata": {
                "trace_id": ctx.trace_id,
                "project_id": ctx.project_id,
                "intent": ctx.intent.get("intent"),
                "complexity": ctx.intent.get("complexity"),
                "sources": {
                    "memories": len(ctx.memories),
                    "knowledge": len(ctx.knowledge),
                    "assets": len(ctx.assets),
                    "skills": len(ctx.skills),
                    "rules": len(ctx.rules)
                },
                "cache_stats": self.cache.get_stats(),
                "fallback_status": self.fallback_manager.get_status(),
            }
        }
        
        ctx.stage_timings["stage_4"] = (time.time() - start) * 1000
        print(f"[{ctx.trace_id}] Stage 4: Context assembled ({ctx.token_estimate}t, ratio:{assembled['compression_ratio']}) ({ctx.stage_timings['stage_4']:.0f}ms)")


# Convenience function
async def execute_pipeline(task: str, project_id: str = "0", 
                          user_id: Optional[str] = None,
                          db: AsyncSession = None) -> PipelineContext:
    """Convenience function to execute pipeline"""
    if db is None:
        raise ValueError("Database session required")
    
    pipeline = ContextPipeline(db)
    return await pipeline.execute(task, project_id, user_id)
