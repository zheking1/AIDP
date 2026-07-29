import json
import urllib.request

CONTROLLER = "http://192.168.0.100:8883"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": "aidp_059193d65f40d73362259df1cd3f373f0d4243300d83b92fa038ccfe49b8ea4b"
}

# Delete all data for project_id=3 via SQLite in container
import subprocess
cmds = [
    'docker exec code-index python3 -c "import sqlite3; c=sqlite3.connect(\\\"/app/data/code_index.db\\\"); print(\\\"nodes:\\\", c.execute(\\\"SELECT COUNT(*) FROM nodes WHERE project_id=3\\\").fetchone()[0]); print(\\\"edges:\\\", c.execute(\\\"SELECT COUNT(*) FROM edges WHERE project_id=3\\\").fetchone()[0]); print(\\\"embeddings:\\\", c.execute(\\\"SELECT COUNT(*) FROM node_embeddings WHERE project_id=3\\\").fetchone()[0]); c.close()"',
]

# First check current counts
print("=== Current data ===")
r = subprocess.run(cmds[0], shell=True, capture_output=True, text=True)
print(r.stdout)

# Delete data
print("=== Deleting old data ===")
delete_cmds = [
    'docker exec code-index python3 -c "import sqlite3; c=sqlite3.connect(\\\"/app/data/code_index.db\\\"); c.execute(\\\"DELETE FROM node_embeddings WHERE project_id=3\\\"); c.execute(\\\"DELETE FROM edges WHERE project_id=3\\\"); c.execute(\\\"DELETE FROM nodes WHERE project_id=3\\\"); c.execute(\\\"DELETE FROM file_fingerprints WHERE project_id=3\\\"); c.commit(); print(\\\"Deleted\\\"); c.close()"',
]
for cmd in delete_cmds:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(r.stdout, r.stderr)

# Verify deletion
print("\n=== After deletion ===")
r = subprocess.run(cmds[0], shell=True, capture_output=True, text=True)
print(r.stdout)
