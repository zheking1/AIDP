# Code Linking

## CodeLinker (`linker.py`)

Links documentation pages to source code entities (classes, functions, methods) for traceability.

### Constructor

```python
class CodeLinker:
    def __init__(self, db: AsyncSession)
```

### `link_document_to_code(doc_id, code_nodes) -> List[CodeLink]`

Creates code reference links from a document to code entities.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_id` | int | Yes | Target documentation page ID |
| `code_nodes` | List[Dict] | Yes | Array of code entity descriptors |

**Code Node Structure**:
```json
{
    "type": "class",
    "name": "MyService",
    "file_path": "src/services/my_service.py",
    "line_start": 42,
    "line_end": 120,
    "language": "python",
    "confidence": 0.85
}
```

**Process**:

1. Iterates over each code node in the input array
2. Creates a `CodeLink` record for each:
   - `node_type`: `class`, `function`, or `method`
   - `node_name`: Entity name (e.g., `MyService`)
   - `file_path`: Source file location
   - `line_start` / `line_end`: Line range in source
   - `language`: Programming language identifier
   - `confidence`: Match confidence (0.0-1.0, default 0.5)
3. Adds all links to the database session
4. Calls `db.commit()` to persist
5. Returns the list of created `CodeLink` objects

### `get_code_links(doc_id) -> List[CodeLink]`

Retrieves all code links for a given document.

```python
select(CodeLink).where(CodeLink.doc_id == doc_id)
```

Returns all linked code entity references.

---

## API Endpoints

All endpoints are in `doc_index.py` under the `tools/doc-index/app/api/` path.

### `POST /api/docs/{doc_id}/link`

Creates links from a document to code nodes.

**Request**:
```json
{
    "code_nodes": [
        {
            "type": "class",
            "name": "UserController",
            "file_path": "src/controllers/user.py",
            "line_start": 10,
            "line_end": 50,
            "language": "python",
            "confidence": 0.9
        }
    ]
}
```

**Response**:
```json
{
    "linked": 1
}
```

**Validation**: Requires `code_nodes` array to be non-empty (400 error if missing).

### `GET /api/docs/{doc_id}/links`

Retrieves all code links for a document.

**Response**:
```json
{
    "links": [
        {
            "node_type": "class",
            "node_name": "UserController",
            "file_path": "src/controllers/user.py",
            "line_start": 10
        }
    ]
}
```

---

## Use Cases

1. **Auto-linking during doc generation**: When AI generates docs, it can simultaneously link to referenced code
2. **Documentation freshness**: Combined with drift detection to identify outdated docs
3. **Code-to-doc navigation**: Enable bidirectional navigation between codebase and docs
4. **Impact analysis**: Find all docs affected by a code change via reverse lookup