#!/usr/bin/env python3
"""Add openCode to file-watcher database directly"""

import sqlite3
import json

def add_watcher():
    db_path = '/home/docker/AI-Code/tools/file-watcher/data/file_watcher.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watched_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL UNIQUE,
            local_path TEXT NOT NULL,
            code_index_project_id INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            ignored_dirs TEXT DEFAULT '[]',
            ignored_patterns TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert project
    try:
        cursor.execute('''
            INSERT INTO watched_projects 
            (project_name, local_path, code_index_project_id, ignored_dirs, ignored_patterns)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            'openCode',
            '/home/docker/AI-Code',
            1,
            json.dumps(['.git', 'node_modules', '__pycache__', '.venv', 'data']),
            json.dumps(['*.pyc', '*.log', '*.tar.gz'])
        ))
        conn.commit()
        print("Added openCode to file-watcher database")
    except sqlite3.IntegrityError:
        print("Project 'openCode' already exists")
    except Exception as e:
        print(f"Error: {e}")
    
    # List projects
    cursor.execute('SELECT id, project_name, local_path FROM watched_projects')
    projects = cursor.fetchall()
    print("\nWatched projects:")
    for p in projects:
        print(f"  ID={p[0]}, Name={p[1]}, Path={p[2]}")
    
    conn.close()

if __name__ == "__main__":
    add_watcher()
