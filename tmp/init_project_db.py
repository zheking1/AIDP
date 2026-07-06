#!/usr/bin/env python3
"""Initialize openCode project directly in database"""

import asyncio
import asyncpg

async def init_project():
    # Connect to PostgreSQL
    conn = await asyncpg.connect(
        host='127.0.0.1',
        port=5432,
        user='novel_os',
        password='jygame_postgres_01',
        database='aidp'
    )
    
    try:
        # Check if project exists
        existing = await conn.fetchrow(
            "SELECT id FROM app_projects WHERE name = 'openCode'"
        )
        
        if existing:
            print(f"Project 'openCode' already exists with ID: {existing['id']}")
            return existing['id']
        
        # Insert project
        project_id = await conn.fetchval("""
            INSERT INTO app_projects (name, description, project_type, owner_id, created_at)
            VALUES ('openCode', 
                    'AIDP (AI DevOps Platform) - AI DevOps Platform with staged context pipeline',
                    'ai-platform',
                    'admin',
                    NOW())
            RETURNING id
        """)
        
        print(f"Created project 'openCode' with ID: {project_id}")
        return project_id
        
    finally:
        await conn.close()

if __name__ == "__main__":
    project_id = asyncio.run(init_project())
    print(f"PROJECT_ID={project_id}")
