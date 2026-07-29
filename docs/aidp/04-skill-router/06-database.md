# Skill Router — Database Schema

PostgreSQL 16 with `pgvector` extension. ORM: SQLAlchemy 2.0 async.

## All Tables (12)

| # | Table              | Primary Key | Purpose                              |
|---|--------------------|-------------|--------------------------------------|
| 1 | `users`            | UUID        | User accounts with roles             |
| 2 | `api_keys`         | UUID        | API key authentication               |
| 3 | `projects`         | UUID        | Project isolation for skills/rules   |
| 4 | `skills`           | UUID        | Registered skills with embeddings    |
| 5 | `skill_files`      | UUID        | Multi-file support for skills        |
| 6 | `skill_groups`     | UUID        | Hierarchical skill organization      |
| 7 | `rules`            | UUID        | Rules with embeddings                |
| 8 | `rule_groups`      | UUID        | Hierarchical rule organization       |
| 9 | `skill_permissions`| UUID        | Per-skill role-based access control  |
| 10| `llm_configs`      | UUID        | LLM model configurations per role    |
| 11| `evolutions`       | UUID        | Versioned content history            |
| 12| `review_patterns`  | UUID        | Regex patterns for content review    |
| 13| `resolve_cache`    | VARCHAR(64) | Redis-backed resolve cache (mirror)  |
| 14| `operation_logs`   | UUID        | Audit trail of all operations        |

---

## 1. `users`

| Column     | Type           | Default          | Constraints              |
|------------|----------------|------------------|--------------------------|
| `id`       | UUID           | `uuid4()`        | PRIMARY KEY              |
| `username` | VARCHAR(100)   | -                | UNIQUE, NOT NULL         |
| `password` | VARCHAR(255)   | -                | NOT NULL (bcrypt hash)   |
| `nickname` | VARCHAR(100)   | `""`             |                          |
| `remark`   | TEXT           | `""`             |                          |
| `role`     | VARCHAR(20)    | `"admin"`        | CHECK: IN ('super_admin','admin','developer','user','readonly') |
| `is_active`| BOOLEAN        | `true`           |                          |
| `created_at`| DateTime      | `utcnow()`       |                          |

**Relationships:** `api_keys`, `projects`, `skill_groups`, `rule_groups` (all cascade delete-orphan)

---

## 2. `api_keys`

| Column     | Type          | Default     | Constraints                          |
|------------|---------------|-------------|--------------------------------------|
| `id`       | UUID          | `uuid4()`   | PRIMARY KEY                          |
| `user_id`  | UUID          | -           | FK → `users.id` ON DELETE CASCADE, NOT NULL |
| `key_hash` | VARCHAR(64)   | -           | UNIQUE, NOT NULL (SHA-256 of plaintext key) |
| `label`    | VARCHAR(100)  | -           | Human-readable label                 |
| `last_used`| DateTime      | -           |                                      |
| `is_active`| BOOLEAN       | `true`      |                                      |
| `created_at`| DateTime     | `utcnow()`  |                                      |

**Relationships:** `user` → User

---

## 3. `projects`

| Column       | Type          | Default     | Constraints                 |
|--------------|---------------|-------------|-----------------------------|
| `id`         | UUID          | `uuid4()`   | PRIMARY KEY                 |
| `user_id`    | UUID          | -           | FK → `users.id`             |
| `name`       | VARCHAR(255)  | -           | NOT NULL                    |
| `slug`       | VARCHAR(255)  | -           | UNIQUE, NOT NULL            |
| `title`      | VARCHAR(255)  | -           | NOT NULL                    |
| `status`     | VARCHAR(50)   | `"active"`  |                             |
| `description`| TEXT          | -           |                             |
| `instruction`| TEXT          | `None`      | Global instruction for skills |
| `config`     | JSON          | `{}`        |                             |
| `settings`   | JSONB         | `{}`        |                             |
| `workspace_id`| UUID         | -           |                             |
| `is_active`  | BOOLEAN       | `true`      |                             |
| `created_at` | DateTime      | `utcnow()`  |                             |
| `updated_at` | DateTime      | `utcnow()`  |                             |

**Relationships:** `user` → User, `skills`, `rules`, `llm_configs`

---

## 4. `skills`

| Column            | Type              | Default        | Constraints                       |
|-------------------|-------------------|----------------|-----------------------------------|
| `id`              | UUID              | `uuid4()`      | PRIMARY KEY                       |
| `name`            | VARCHAR(255)      | -              | NOT NULL                          |
| `description`     | TEXT              | -              |                                   |
| `instruction`     | TEXT              | `None`         | Per-skill guidance                |
| `content`         | TEXT              | -              | NOT NULL                          |
| `tags`            | ARRAY(VARCHAR)    | `[]`           |                                   |
| `user_id`         | UUID              | -              | FK → `users.id`, NOT NULL         |
| `version`         | Integer           | `1`            |                                   |
| `dependencies`    | ARRAY(UUID)       | `[]`           | Skill dependency graph            |
| `exec_config`     | JSON              | `None`         | Execution config dict             |
| `embedding`       | Vector(1024)      | -              | pgvector embedding                |
| `review_status`   | VARCHAR(20)       | `"pending"`    | Values: pending/approved/rejected |
| `review_report`   | TEXT              | -              | Review result                     |
| `review_log`      | ARRAY(TEXT)       | `[]`           |                                   |
| `allow_risk_patterns` | ARRAY(TEXT)   | `[]`           | Exempted risk pattern IDs         |
| `scope`           | VARCHAR(20)       | `"private"`    | `"private"` or `"public"`         |
| `allowed_roles`   | ARRAY(VARCHAR)    | `None`         | RBAC: roles that can use this skill |
| `sensitive`       | BOOLEAN           | `false`        | Requires secondary approval       |
| `weight_config`   | JSONB             | `None`         | Custom scoring weights            |
| `is_active`       | BOOLEAN           | `true`         |                                   |
| `project_id`      | UUID              | -              | FK → `projects.id`                |
| `group_id`        | UUID              | -              | FK → `skill_groups.id`            |
| `source_url`      | VARCHAR(500)      | -              | Origin URL (GitHub etc.)          |
| `source_type`     | VARCHAR(20)       | -              | `"github"` or `"clawhub"`         |
| `source_id`       | VARCHAR(255)      | -              | `owner/repo/path` or slug         |
| `examples`        | ARRAY(TEXT)       | `[]`           | Example queries for embedding     |
| `created_at`      | DateTime          | `utcnow()`     |                                   |
| `updated_at`      | DateTime          | `utcnow()`     |                                   |

**Relationships:** `project` → Project, `group` → SkillGroup, `files` → SkillFile (cascade delete-orphan), `permissions` → SkillPermission (cascade delete-orphan)

**Indexes:**
- `idx_skill_embedding_hnsw` — HNSW index on `embedding` (vector_cosine_ops, m=16, ef_construction=64)
- `idx_skills_user_active` — Composite on `(user_id, is_active)`
- `idx_skills_scope_active` — Composite on `(scope, is_active)`
- `idx_skills_tags_gin` — GIN index on `tags` (array)
- `idx_skills_review_status` — B-tree on `review_status`
- `idx_skills_group_id` — B-tree on `group_id`

---

## 5. `skill_files`

| Column     | Type          | Default     | Constraints                              |
|------------|---------------|-------------|------------------------------------------|
| `id`       | UUID          | `uuid4()`   | PRIMARY KEY                              |
| `skill_id` | UUID          | -           | FK → `skills.id` ON DELETE CASCADE, NOT NULL |
| `path`     | VARCHAR(500)  | -           | NOT NULL (file path within skill)         |
| `content`  | TEXT          | -           | NOT NULL                                 |
| `language` | VARCHAR(20)   | `"text"`    |                                           |
| `is_entry` | BOOLEAN       | `false`     | Is this the entry-point file?            |
| `sort_order`| Integer      | `0`         |                                           |
| `created_at`| DateTime     | `utcnow()`  |                                           |

**Relationships:** `skill` → Skill

---

## 6. `skill_groups`

| Column     | Type          | Default     | Constraints                          |
|------------|---------------|-------------|--------------------------------------|
| `id`       | UUID          | `uuid4()`   | PRIMARY KEY                          |
| `name`     | VARCHAR(255)  | -           | NOT NULL                             |
| `parent_id`| UUID          | -           | FK → `skill_groups.id` (self-ref)    |
| `user_id`  | UUID          | -           | FK → `users.id`, NOT NULL            |
| `sort_order`| Integer      | `0`         |                                      |
| `created_at`| DateTime     | `utcnow()`  |                                      |
| `updated_at`| DateTime     | `utcnow()`  |                                      |

**Relationships:** `user` → User, `parent` → SkillGroup (self), `children` → SkillGroup (ordered by sort_order), `skills` → Skill

**Indexes:** `idx_skill_groups_user_id`, `idx_skill_groups_parent_id`

---

## 7. `rules`

| Column       | Type              | Default     | Constraints                    |
|--------------|-------------------|-------------|--------------------------------|
| `id`         | UUID              | `uuid4()`   | PRIMARY KEY                    |
| `name`       | VARCHAR(255)      | -           | NOT NULL                       |
| `content`    | TEXT              | -           | NOT NULL                       |
| `tags`       | ARRAY(VARCHAR)    | `[]`        |                                |
| `priority`   | Integer           | `0`         |                                |
| `user_id`    | UUID              | -           | FK → `users.id`, NOT NULL      |
| `embedding`  | Vector(1024)      | -           |                                |
| `version`    | Integer           | `1`         |                                |
| `project_id` | UUID              | -           | FK → `projects.id`             |
| `group_id`   | UUID              | -           | FK → `rule_groups.id`          |
| `scope`      | VARCHAR(20)       | `"private"` |                                |
| `allowed_roles` | ARRAY(VARCHAR) | `None`      |                                |
| `is_active`  | BOOLEAN           | `true`      |                                |
| `created_at` | DateTime          | `utcnow()`  |                                |
| `updated_at` | DateTime          | `utcnow()`  |                                |

**Relationships:** `project` → Project, `group` → RuleGroup

**Indexes:**
- `idx_rule_embedding_hnsw` — HNSW index on `embedding` (vector_cosine_ops, m=16, ef_construction=64)
- `idx_rules_group_id` — B-tree on `group_id`

---

## 8. `rule_groups`

| Column     | Type          | Default     | Constraints                         |
|------------|---------------|-------------|-------------------------------------|
| `id`       | UUID          | `uuid4()`   | PRIMARY KEY                         |
| `name`     | VARCHAR(255)  | -           | NOT NULL                            |
| `parent_id`| UUID          | -           | FK → `rule_groups.id` (self-ref)    |
| `user_id`  | UUID          | -           | FK → `users.id`, NOT NULL           |
| `sort_order`| Integer      | `0`         |                                     |
| `created_at`| DateTime     | `utcnow()`  |                                     |
| `updated_at`| DateTime     | `utcnow()`  |                                     |

**Relationships:** `user` → User, `parent` → RuleGroup (self), `children` → RuleGroup, `rules` → Rule

**Indexes:** `idx_rule_groups_user_id`, `idx_rule_groups_parent_id`

---

## 9. `skill_permissions`

| Column         | Type          | Default     | Constraints                          |
|----------------|---------------|-------------|--------------------------------------|
| `id`           | UUID          | `uuid4()`   | PRIMARY KEY                          |
| `skill_id`     | UUID          | -           | FK → `skills.id` ON DELETE CASCADE, NOT NULL |
| `allowed_roles`| ARRAY(VARCHAR)| `None`      | Roles allowed to access              |
| `denied_roles` | ARRAY(VARCHAR)| `None`      | Roles explicitly denied              |
| `created_at`   | DateTime      | `utcnow()`  |                                      |

**Relationships:** `skill` → Skill

**Indexes:** `idx_skill_permissions_skill_id`

---

## 10. `llm_configs`

| Column       | Type          | Default     | Constraints                    |
|--------------|---------------|-------------|--------------------------------|
| `id`         | UUID          | `uuid4()`   | PRIMARY KEY                    |
| `name`       | VARCHAR(100)  | -           | NOT NULL                       |
| `endpoint`   | VARCHAR(500)  | -           | NOT NULL                       |
| `api_key`    | VARCHAR(500)  | -           | NOT NULL                       |
| `model_name` | VARCHAR(100)  | -           |                                |
| `role`       | VARCHAR(50)   | -           | CHECK: IN ('Intent Analyzer','Embedding','Review','Ranker') |
| `temperature`| Float         | `0.7`       |                                |
| `max_tokens` | Integer       | `2048`      |                                |
| `timeout_secs`| Integer      | `30`        |                                |
| `is_healthy` | BOOLEAN       | `true`      |                                |
| `is_default` | BOOLEAN       | `false`     | Per-role default model         |
| `user_id`    | UUID          | -           | FK → `users.id`, NOT NULL      |
| `project_id` | UUID          | -           | FK → `projects.id`             |
| `created_at` | DateTime      | `utcnow()`  |                                |

**Relationships:** `project` → Project

---

## 11. `evolutions`

| Column         | Type          | Default      | Constraints                          |
|----------------|---------------|--------------|--------------------------------------|
| `id`           | UUID          | `uuid4()`    | PRIMARY KEY                          |
| `target_type`  | VARCHAR(10)   | -            | NOT NULL (`"skill"` or `"rule"`)     |
| `target_id`    | UUID          | -            | NOT NULL                             |
| `target_name`  | VARCHAR(255)  | -            | NOT NULL                             |
| `old_version`  | Integer       | -            | NOT NULL                             |
| `old_content`  | TEXT          | -            | NOT NULL                             |
| `new_content`  | TEXT          | -            | NOT NULL                             |
| `diff_summary` | TEXT          | -            |                                      |
| `trigger_reason`| TEXT         | -            | NOT NULL                             |
| `status`       | VARCHAR(20)   | `"applied"`  | Values: pending/applied/rejected/rolled_back |
| `applied_by`   | VARCHAR(100)  | `"local"`    |                                      |
| `user_id`      | UUID          | -            | FK → `users.id`, NOT NULL            |
| `rollback_to`  | UUID          | -            | FK → `evolutions.id` (nullable)      |
| `created_at`   | DateTime      | `utcnow()`   |                                      |
| `applied_at`   | DateTime      | -            |                                      |

---

## 12. `review_patterns`

| Column      | Type          | Default     | Constraints                     |
|-------------|---------------|-------------|----------------------------------|
| `id`        | UUID          | `uuid4()`   | PRIMARY KEY                      |
| `name`      | VARCHAR(100)  | -           | NOT NULL                         |
| `pattern`   | VARCHAR(500)  | -           | NOT NULL (regex)                 |
| `risk_level`| VARCHAR(20)   | `"high"`    |                                  |
| `is_active` | BOOLEAN       | `true`      |                                  |
| `user_id`   | UUID          | -           | FK → `users.id`, NOT NULL        |
| `created_at`| DateTime      | `utcnow()`  |                                  |
| `updated_at`| DateTime      | `utcnow()`  |                                  |

---

## 13. `resolve_cache` (PostgreSQL mirror, primary is Redis)

| Column       | Type          | Default     | Constraints                     |
|--------------|---------------|-------------|----------------------------------|
| `key_hash`   | VARCHAR(64)   | -           | PRIMARY KEY                      |
| `user_id`    | UUID          | -           | FK → `users.id`, NOT NULL        |
| `task_hash`  | VARCHAR(64)   | -           | NOT NULL                         |
| `result`     | JSON          | -           | NOT NULL                         |
| `ttl_seconds`| Integer       | `3600`      |                                  |
| `created_at` | DateTime      | `utcnow()`  |                                  |
| `expires_at` | DateTime      | -           |                                  |

---

## 14. `operation_logs`

| Column         | Type          | Default     | Constraints                    |
|----------------|---------------|-------------|--------------------------------|
| `id`           | UUID          | `uuid4()`   | PRIMARY KEY                    |
| `user_id`      | UUID          | -           | FK → `users.id`, NOT NULL      |
| `resource_type`| VARCHAR(50)   | -           | NOT NULL                       |
| `resource_id`  | UUID          | -           |                                |
| `action`       | VARCHAR(50)   | -           | NOT NULL                       |
| `detail`       | JSON          | -           | Full operation details          |
| `trace_id`     | VARCHAR(64)   | -           |                                |
| `created_at`   | DateTime      | `utcnow()`  |                                |

---

## Indexes Summary

| Index Name                     | Table       | Type   | Columns / Expression                          |
|-------------------------------|-------------|--------|-----------------------------------------------|
| PK (implicit)                  | all         | B-tree | Primary keys                                   |
| FK (implicit)                  | referencing | B-tree | Foreign key columns                            |
| `idx_skill_embedding_hnsw`     | skills      | HNSW   | `embedding vector_cosine_ops` (m=16, ef=64)   |
| `idx_rule_embedding_hnsw`      | rules       | HNSW   | `embedding vector_cosine_ops` (m=16, ef=64)   |
| `idx_skills_user_active`       | skills      | B-tree | `(user_id, is_active)`                        |
| `idx_skills_scope_active`      | skills      | B-tree | `(scope, is_active)`                          |
| `idx_skills_tags_gin`          | skills      | GIN    | `tags`                                        |
| `idx_skills_review_status`     | skills      | B-tree | `review_status`                               |
| `idx_skills_group_id`          | skills      | B-tree | `group_id`                                    |
| `idx_rules_group_id`           | rules       | B-tree | `group_id`                                    |
| `idx_skill_groups_user_id`     | skill_groups| B-tree | `user_id`                                     |
| `idx_skill_groups_parent_id`   | skill_groups| B-tree | `parent_id`                                   |
| `idx_rule_groups_user_id`      | rule_groups | B-tree | `user_id`                                     |
| `idx_rule_groups_parent_id`    | rule_groups | B-tree | `parent_id`                                   |
| `idx_skill_permissions_skill_id`| skill_permissions | B-tree | `skill_id`                           |