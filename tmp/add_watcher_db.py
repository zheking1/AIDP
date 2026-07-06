#!/usr/bin/env python3
"""Add openCode to file-watcher database directly"""

import asyncio
import aiosqlite
import json

async def add_watcher():
    db_path = '/home/docker/AI-Code/tools/file-watcher/data/file_watcher.db'
    
    async with aiosqlite.connect(db_path) as db:
        # Create table if not exists
        await db.execute('''
            CREATE TABLE IF NOT EXISTS watched_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL UNIQUE,
                local_path TEXT NOT NULL,
                code_index_project_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                ignored_dirs TEXT DEFAULT '[]',
                ignored_patterns TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert project
        try:
            await db.execute('''
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
            await db.commit()
            print("Added openCode to file-watcher database")
        except Exception as e:
            print(f"Error: {e}")
        
        # List projects
        cursor = await db.execute('SELECT id, project_name, local_path FROM watched_projects')
        projects = await cursor.fetchall()
        print("\nWatched projects:")
        for p in projects:
            print(f"  ID={p[0]}, Name={p[1]}, Path={p[2]}")

if __name__ == "__main__":
    asyncio.run(add_watcher())
