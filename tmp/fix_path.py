#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/home/docker/AI-Code/tools/file-watcher/data/file_watcher.db')
cursor = conn.cursor()
cursor.execute("UPDATE watched_projects SET local_path = '/watched-projects' WHERE local_path = '/home/docker/AI-Code'")
conn.commit()
print('Updated rows:', cursor.rowcount)
cursor.execute('SELECT id, project_name, local_path FROM watched_projects')
print('Projects:', cursor.fetchall())
conn.close()
