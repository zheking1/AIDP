# Drift Detection

## DriftDetector (`drift_detector.py`)

Detects when documentation becomes outdated due to code changes. Creates `DocDrift` records for affected sections.

### Constructor

```python
class DriftDetector:
    def __init__(self, db: AsyncSession)
```

### `detect_drift(doc_id, code_changes) -> List[DocDrift]`

Analyzes code changes and identifies documentation sections that may be stale.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_id` | int | Yes | Documentation page ID to check |
| `code_changes` | List[Dict] | Yes | Array of code change descriptors |

**Code Change Structure**:
```json
{
    "affected_sections": ["Installation", "Configuration"],
    "score": 0.75
}
```

**Process**:

1. Look up the `DocPage` by `doc_id`
2. If the page exists and the change lists `affected_sections`:
   - For each affected section heading, create a `DocDrift` record:
     - `doc_id`: The documentation page
     - `section_heading`: Name of the outdated section
     - `drift_score`: Severity score (0.0-1.0, defaults to 0.5)
     - `status`: Always `"detected"` on creation
3. Commit all drift records in a single transaction

**Returns**: List of created `DocDrift` objects, or empty list if no drifts detected.

### `get_drifts(doc_id) -> List[DocDrift]`

Retrieves all active (unresolved) drifts for a document.

```python
select(DocDrift).where(
    DocDrift.doc_id == doc_id,
    DocDrift.status == "detected"
).order_by(DocDrift.detected_at.desc())
```

- Only returns drifts with `status == "detected"`
- Ordered by most recent detection first

---

## API Endpoints

### `POST /api/docs/{doc_id}/drift`

Submit code changes for drift analysis.

**Request**:
```json
{
    "changes": [
        {
            "affected_sections": ["API Reference", "Quick Start"],
            "score": 0.85
        },
        {
            "affected_sections": ["Configuration"],
            "score": 0.5
        }
    ]
}
```

**Response**:
```json
{
    "drifts_detected": 3
}
```

Three drift records created: 2 for "API Reference" + "Quick Start" (from change 1), and 1 for "Configuration" (from change 2).

### `GET /api/docs/{doc_id}/drifts`

Retrieve active drifts for a document.

**Response**:
```json
{
    "drifts": [
        {
            "section": "API Reference",
            "score": 0.85,
            "status": "detected"
        },
        {
            "section": "Configuration",
            "score": 0.5,
            "status": "detected"
        }
    ]
}
```

---

## Integration with Code Linking

Drift detection and code linking work together:

1. **Code Linking** establishes which code entities a doc references
2. **Drift Detection** monitors those linked entities for changes
3. When a linked code file changes, the agent submits affected sections and scores
4. Stale documentation can be flagged and prioritized for updates

## Use Cases

1. **Continuous doc validation**: Run after each code commit to identify stale docs
2. **Priority queue**: Sort by `drift_score` to update most-critical docs first
3. **Doc freshness dashboard**: Aggregate all unresolved drifts across projects
4. **CI integration**: Block PRs if documentation drifts exceed a threshold