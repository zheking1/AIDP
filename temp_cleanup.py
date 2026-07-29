import sqlite3

c = sqlite3.connect('/app/data/code_index.db')

print('Before:')
print('  nodes:', c.execute('SELECT COUNT(*) FROM nodes WHERE project_id=3').fetchone()[0])
print('  edges:', c.execute('SELECT COUNT(*) FROM edges WHERE project_id=3').fetchone()[0])
print('  embeddings:', c.execute('SELECT COUNT(*) FROM node_embeddings WHERE project_id=3').fetchone()[0])
print('  fingerprints:', c.execute('SELECT COUNT(*) FROM file_fingerprints WHERE project_id=3').fetchone()[0])

c.execute('DELETE FROM node_embeddings WHERE project_id=3')
c.execute('DELETE FROM edges WHERE project_id=3')
c.execute('DELETE FROM nodes WHERE project_id=3')
c.execute('DELETE FROM file_fingerprints WHERE project_id=3')
c.commit()

print('\nAfter:')
print('  nodes:', c.execute('SELECT COUNT(*) FROM nodes WHERE project_id=3').fetchone()[0])
print('  edges:', c.execute('SELECT COUNT(*) FROM edges WHERE project_id=3').fetchone()[0])
print('  embeddings:', c.execute('SELECT COUNT(*) FROM node_embeddings WHERE project_id=3').fetchone()[0])
print('  fingerprints:', c.execute('SELECT COUNT(*) FROM file_fingerprints WHERE project_id=3').fetchone()[0])

c.close()
print('\nDone!')
