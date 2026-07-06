#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/home/docker/AI-Code/tools/file-watcher/data/file_watcher.db')
cursor = conn.cursor()
cursor.execute("UPDATE watched_projects SET is_active = 1 WHERE is_active IS NULL")
conn.commit()
print('Updated rows:', cursor.rowcount)
cursor.execute('SELECT id, project_name, is_active FROM watched_projects')
print('Projects:', cursor.fetchall())
conn.close()
