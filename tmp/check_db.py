#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/app/data/file_watcher.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM watched_projects')
print('Projects:', cursor.fetchall())
conn.close()
