# Contradiction Detection

## SemanticContradictionDetector

Detects contradictions between new and existing memories using two complementary strategies.

### Init

```python
detector = SemanticContradictionDetector()
```

Pre-defines negation patterns and negation words (Chinese + English).

**Negation Patterns** (regex):
```
不要, 禁止, 不能, 不应该, 避免,
do not, don't, should not, avoid, never,
不建议, 不推荐, 禁止使用
```

**Negation Words** (set matching):
```
不, 没, 未, 非, 别, 莫, 勿,
no, not, never, don't
```

### `detect(new_memory, existing_memories) -> List[Dict]`

Main detection method:

```python
def detect(self, new_memory: Dict, existing_memories: List[Dict]) -> List[Dict]
```

Iterates over all existing memories and runs two checks per pair:

#### Check 1: Negation Pattern (`_check_negation_pattern`)

Algorithm:
1. For each negation pattern, test if it appears in text1 XOR text2
2. If one text has a negation pattern but the other does not:
   - Compute word overlap between the two texts
   - If overlap > 3 words → flag as negation contradiction

#### Check 2: Semantic Reversal (`_check_semantic_reversal`)

Algorithm:
1. Extract word sets from both texts (lowercased)
2. Compute word overlap; if < 3 words → no contradiction
3. Check if exactly one text contains negation words
4. If one has negations and the other does not → flag as semantic_reversal

### Detection Result

```json
{
    "existing_memory": { "id": "...", "title": "...", "content": "..." },
    "contradiction_type": "negation" | "semantic_reversal",
    "confidence": 0.6 | 0.8,
    "evidence": "new: [title] existing: [title]"
}
```

**Confidence calculation**:
- `0.8` if both negation pattern AND semantic reversal detected
- `0.6` if only one type detected

---

## ContradictionHandler

Defines resolution strategies based on contradiction confidence.

### `handle(new_memory, existing_memory, contradiction_type, confidence) -> Dict`

| Confidence | Action | Reason |
|------------|--------|--------|
| `> 0.8` | `flag_for_review` | High confidence - needs manual review |
| `> 0.6` | `update_existing` or `keep_both` | Medium: replaces if newer, else keeps both |
| `<= 0.6` | `keep_both` | Low confidence - possibly different contexts |

**Logic for medium confidence (0.6+)**:
```python
if new_time > old_time:
    action = "update_existing"   # New memory takes precedence
else:
    action = "keep_both"         # Keep both for reference
```

---

## Integration in Tool Protocol

The `memory.contradiction.check` capability in `tool.py`:

```python
elif req.capability == "memory.contradiction.check":
    # Load up to 100 existing memories for the project
    detector = SemanticContradictionDetector()
    contradictions = detector.detect(
        {"title": input_title, "content": input_content},
        [{"id": e.id, "title": e.title, "content": e.content,
          "createdAt": str(e.created_at)} for e in existing_list]
    )
    # Apply contradiction handler to each result
    handler = ContradictionHandler()
    for c in contradictions:
        action = handler.handle(...)
        results.append({"contradiction": c, "action": action})

    return {"has_contradictions": len(results) > 0, "contradictions": results}
```

This capability should be called **before** creating a new memory to check for conflicts with existing project memories.