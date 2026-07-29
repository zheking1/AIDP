# Skill Router — Rule Management

Rules are stored as `Rule` records in PostgreSQL with vector embeddings for semantic search during task resolution. The rule service (`app/services/rule_service.py`) provides full CRUD.

## Rule Model (`db/models.py:210`)

```python
class Rule(Base):
    __tablename__ = "rules"

    id            = UUID pk, default uuid4
    name          = VARCHAR(255)
    content       = Text NOT NULL
    tags          = ARRAY(VARCHAR), default=list
    priority      = Integer, default=0
    user_id       = UUID FK → users.id
    embedding     = Vector(1024)
    version       = Integer, default=1
    project_id    = UUID FK → projects.id (nullable)
    group_id      = UUID FK → rule_groups.id (nullable)
    scope         = VARCHAR(20), default="private"  # "private" or "public"
    allowed_roles = ARRAY(VARCHAR), default=None
    is_active     = BOOLEAN, default=True
    created_at    = DateTime
    updated_at    = DateTime

    project = relationship → Project
    group   = relationship → RuleGroup
```

## CRUD Operations

### Create Rule

```python
async def create_rule(
    session: AsyncSession,
    user_id: UUID,
    name: str,
    content: str,
    tags: Optional[list] = None,   # default []
    priority: int = 0,
) -> Rule:
    rule = Rule(name=name, content=content, tags=tags or [], priority=priority, user_id=user_id)
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule
```

Called via MCP tool `rule_create` which also supports:
- **Auto-classification:** If `auto_classify=True` and no tags provided, the `ClassificationService` analyzes rule content and generates tags.
- **Auto-grouping:** If `group_name` is specified (or suggested by classifier), the group is auto-created if it doesn't exist.
- **Embedding generation is NOT automatic** — must be triggered separately.

### Update Rule

```python
async def update_rule(
    session: AsyncSession,
    rule_id: UUID,
    name: str = None,         # None = no change
    content: str = None,
    tags: list = None,
    priority: int = None,
    is_active: bool = None,
) -> Optional[Rule]:
    rule = await session.get(Rule, rule_id)
    if not rule:
        return None
    updates = {"name": name, "content": content, "tags": tags, "priority": priority, "is_active": is_active}
    for k, v in updates.items():
        if v is not None:
            setattr(rule, k, v)
    await session.commit()
    await session.refresh(rule)
    return rule
```

Partial updates: only provided fields are changed. MCP tool `rule_update` accepts `tags` as comma-separated string → split to list.

### Delete Rule

```python
async def delete_rule(session: AsyncSession, rule_id: UUID) -> bool:
    rule = await session.get(Rule, rule_id)
    if not rule:
        return False
    await session.delete(rule)
    await session.commit()
    return True
```

### Get Rule

```python
async def get_rule(session: AsyncSession, rule_id: UUID) -> Optional[Rule]:
    return await session.get(Rule, rule_id)
```

### List Rules

```python
async def list_rules(
    session: AsyncSession,
    user_id: UUID,
    tags: Optional[list] = None,       # Filter by tag overlap
    query: Optional[str] = None,       # ILIKE search on name + content
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Rule], int]:           # Returns (items, total_count)
```

Query construction:
```python
stmt = select(Rule).where(Rule.user_id == user_id, Rule.is_active == True)
if tags:
    stmt = stmt.where(Rule.tags.overlap(tags))    # PostgreSQL array overlap
if query:
    stmt = stmt.where(or_(Rule.name.ilike(f"%{query}%"), Rule.content.ilike(f"%{query}%")))
# Ordered by priority DESC, then updated_at DESC
stmt = stmt.order_by(Rule.priority.desc(), Rule.updated_at.desc()).offset(offset).limit(limit)
```

## How Rules Are Stored

Rules have a `Vector(1024)` embedding column with **HNSW index** for fast similarity search:

```sql
CREATE INDEX idx_rule_embedding_hnsw ON rules
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

Additional indexes:
```sql
CREATE INDEX idx_rules_group_id ON rules(group_id);
-- Composite indexes inherited from skill init
```

## How Rules Are Searched (in Resolve)

During `resolve_skills()`, rules are searched in parallel with skills using the same query embedding:

```python
# Vector mode
rule_sql = select(Rule).where(
    Rule.is_active == True,
    Rule.embedding.isnot(None),
    (Rule.user_id == user_id) | (Rule.scope == "public")
)
rule_sql = rule_sql.add_columns(
    (1 - Rule.embedding.cosine_distance(text(f"'{emb_str}'::vector"))).label("vec_score")
).order_by(text("vec_score DESC")).limit(top_k * 2)
```

**Non-vector mode** (tag_only / embedding failed):
```python
rule_sql = select(Rule).where(
    Rule.is_active == True,
    (Rule.user_id == user_id) | (Rule.scope == "public")
).order_by(Rule.priority.desc()).limit(top_k * 2)
```

Rules are scored with the same formula: `final_score = (vec_score * 0.6) + (tag_score * 0.3)`, then sorted by `priority` descending in the final output.

## Rule Groups (`rule_groups` table)

Rules can be organized into hierarchical groups:

```python
class RuleGroup(Base):
    __tablename__ = "rule_groups"
    id         = UUID pk
    name       = VARCHAR(255)
    parent_id  = UUID FK → rule_groups.id (self-referencing, nullable)
    user_id    = UUID FK → users.id
    sort_order = Integer, default=0
    created_at = DateTime
    updated_at = DateTime

    parent   = relationship → RuleGroup (self-ref)
    children = relationship → RuleGroup (ordered by sort_order)
    rules    = relationship → Rule
```

REST API endpoints for rule groups:
- `GET  /api/rule-groups`          — List groups with rule count
- `POST /api/rule-groups`          — Create group (name uniqueness check)
- `PATCH /api/rule-groups/{id}`    — Update name, parent_id, sort_order
- `DELETE /api/rule-groups/{id}`   — Delete (blocks if has children; ungroups rules)
- `POST /api/rules/{id}/move`      — Move rule to another group

## Rule Evolution

Rules support versioned evolution (see `evolution_service.py`):

```python
# Submit evolution
evo = await submit_evolution(session, user_id, rule_id, "rule", new_content, trigger_reason)
# Increments rule.version, stores old/new content in evolutions table

# Rollback
evo = await rollback_evolution(session, evolution_id, trigger_reason)
# Restores rule.content to evo.old_content, increments version again
```