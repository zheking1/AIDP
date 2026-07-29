import sqlite3
c = sqlite3.connect('/app/data/code_index.db')
print('nodes:', c.execute('SELECT COUNT(*) FROM nodes WHERE project_id=3').fetchone()[0])
print('edges:', c.execute('SELECT COUNT(*) FROM edges WHERE project_id=3').fetchone()[0])
print('embeddings:', c.execute('SELECT COUNT(*) FROM node_embeddings WHERE project_id=3').fetchone()[0])
print('fingerprints:', c.execute('SELECT COUNT(*) FROM file_fingerprints WHERE project_id=3').fetchone()[0])
# Check embedding model
r = c.execute('SELECT embedding_model FROM node_embeddings WHERE project_id=3 LIMIT 1').fetchone()
if r: print('embedding_model:', r[0])
c.close()
