import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ContextAssembler:
    """Stage 4: 组装最终 context package"""

    MAX_CONTEXT_TOKENS = 3000
    PRIORITY = ["code_index", "skills", "knowledge", "memories", "assets"]

    async def assemble(
        self,
        instructions: dict,
        intent: dict,
        staged_results: dict,
        skills: list,
    ) -> dict:
        sections = []

        # 1. Role and task summary (highest priority)
        role_text = instructions.get("role", "")
        if role_text:
            sections.append(f"[Role]\n{role_text[:300]}")

        constraints = instructions.get("constraints", {})
        if constraints:
            sections.append(f"[Constraints]\n{json.dumps(constraints, indent=2)[:300]}")

        # 2. Task intent
        if intent:
            sections.append(f"[Intent]\n{json.dumps(intent, indent=2)[:200]}")

        # 3. Skills
        if skills:
            skill_texts = []
            for s in skills[:2]:
                inst = s.get("instruction") or s.get("description") or ""
                skill_texts.append(f"- {s.get('name', '?')}: {inst[:200]}")
            if skill_texts:
                sections.append("[Skills]\n" + "\n".join(skill_texts))

        # 4. Code context
        for key in self.PRIORITY:
            raw = staged_results.get(key, {})
            if isinstance(raw, dict) and raw.get("items"):
                items = raw["items"][:5] if isinstance(raw["items"], list) else [raw["items"]]
                lines = []
                for item in items:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("title") or item.get("qualified_name", "?")
                        desc = item.get("description") or item.get("content") or ""
                        lines.append(f"- {name}: {self._truncate(desc, 150)}")
                    elif isinstance(item, str):
                        lines.append(f"- {self._truncate(item, 150)}")
                if lines:
                    sections.append(f"[{key}]\n" + "\n".join(lines[:8]))

        # 5. Relevant rules
        rules = instructions.get("rules", [])
        relevant_ids = intent.get("relevant_rules", []) if intent else []
        if rules and relevant_ids:
            matched = [r for r in rules if r.get("id") in relevant_ids]
            if matched:
                rule_text = "\n".join(f"- {r.get('category', '')}: {r.get('content', '')[:200]}" for r in matched[:3])
                sections.append(f"[Rules]\n{rule_text}")

        context = "\n\n".join(sections)
        estimated_tokens = len(context) // 3

        if estimated_tokens > self.MAX_CONTEXT_TOKENS:
            context = context[:self.MAX_CONTEXT_TOKENS * 3]

        return {
            "context": context,
            "estimated_tokens": min(estimated_tokens, self.MAX_CONTEXT_TOKENS),
            "sections": len(sections),
        }

    def _truncate(self, text: str, max_len: int) -> str:
        if text and len(text) > max_len:
            return text[:max_len] + "..."
        return text or ""


class InstructionAssembler:
    """Stage 4: 生成 Subagent 专属 Instructions"""

    async def generate_subagent_instructions(
        self,
        task: str,
        parent_instructions: dict,
        domain: str,
        context: dict,
        skills: list,
    ) -> dict:
        agent_type = f"subagent:{domain}"

        allowed_tools = ["code-index", "quality-tool", "sandbox-tool"]
        parent_allowed = (parent_instructions.get("constraints") or {}).get("preferred_tools", [])
        if parent_allowed:
            allowed_tools = [t for t in parent_allowed if t in allowed_tools]

        relevant_files = []
        code_data = context.get("code-index", {})
        if isinstance(code_data, dict):
            items = code_data.get("items", []) if isinstance(code_data.get("items"), list) else []
            relevant_files = [f.get("name", "") for f in items[:3] if isinstance(f, dict)]

        patterns = []
        for s in (skills or [])[:2]:
            if isinstance(s, dict):
                inst = s.get("instruction") or ""
                if inst:
                    patterns.append(inst[:300])

        constraints_text = []
        rules = parent_instructions.get("rules", [])
        if rules:
            constraints_text = [r.get("content", "")[:200] for r in rules[:3]]

        subagent_instructions = {
            "agent_type": agent_type,
            "role": f"You are a specialized developer for the {domain} module. Focus only on {domain}-related code and documentation.",
            "task": task,
            "context": {
                "relevant_files": relevant_files,
                "patterns": patterns,
                "constraints": constraints_text,
            },
            "allowed_tools": allowed_tools,
            "forbidden_tools": ["skill-router", "knowledge-tool"],
        }

        return subagent_instructions

    async def build_agent_context(
        self,
        instructions: dict,
        intent: dict,
        staged_results: dict,
        skills: list,
    ) -> dict:
        assembler = ContextAssembler()
        assembled = await assembler.assemble(instructions, intent, staged_results, skills)

        return {
            "instructions": instructions,
            "intent": intent,
            "skills": skills[:3] if skills else [],
            "assembled_context": assembled,
        }