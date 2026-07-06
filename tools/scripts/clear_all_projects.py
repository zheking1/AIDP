"""Clear all project data from AIDP tools."""
import httpx
import asyncio
import os
import glob
import sqlite3

AIDP_BASE = "http://127.0.0.1"
CONTROLLER = f"{AIDP_BASE}:8883"
CODE_INDEX = f"{AIDP_BASE}:18086"
KNOWLEDGE = f"{AIDP_BASE}:18081"
MEMORY = f"{AIDP_BASE}:18085"
ASSET = f"{AIDP_BASE}:18082"


async def login():
    async with httpx.AsyncClient() as c:
        await c.post(f"{CONTROLLER}/api/auth/login", json={
            "username": os.environ.get("ADMIN_USERNAME", "admin"),
            "password": os.environ.get("ADMIN_PASSWORD", "admin123"),
        })


async def clear_controller():
    print("Clearing Controller projects...")
    async with httpx.AsyncClient() as c:
        await login()
        resp = await c.get(f"{CONTROLLER}/api/projects/")
        projects = resp.json().get("projects", [])
        print(f"  Found {len(projects)} projects")
        for p in projects:
            await c.delete(f"{CONTROLLER}/api/projects/{p['id']}")
            print(f"  Deleted project: {p['name']} (id={p['id']})")
    print("Controller cleared.\n")


async def clear_code_index():
    print("Clearing code-index data...")
    db_files = glob.glob("tools/code-index/data/*.db")
    for db_file in db_files:
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM projects")
            projects = cursor.fetchall()
            print(f"  Found {len(projects)} projects in {db_file}")
            for pid, name in projects:
                cursor.execute("DELETE FROM edges WHERE project_id = ?", (pid,))
                cursor.execute("DELETE FROM nodes WHERE project_id = ?", (pid,))
                cursor.execute("DELETE FROM projects WHERE id = ?", (pid,))
                print(f"  Deleted project: {name} (id={pid})")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  Error clearing {db_file}: {e}")
    print("code-index cleared.\n")


async def clear_knowledge():
    print("Clearing knowledge-tool documents...")
    async with httpx.AsyncClient() as c:
        resp = await c.get(f"{KNOWLEDGE}/api/documents", params={
            "workspace_id": "default",
            "page_size": 100,
        })
        docs = resp.json().get("data", [])
        print(f"  Found {len(docs)} documents")
        for doc in docs:
            doc_id = doc.get("id") or doc.get("document_id")
            if doc_id:
                await c.delete(f"{KNOWLEDGE}/api/documents/{doc_id}", params={
                    "workspace_id": "default",
                })
                print(f"  Deleted document: {doc.get('title')} (id={doc_id})")
    print("knowledge-tool cleared.\n")


async def clear_memory():
    print("Clearing memory-tool entries...")
    async with httpx.AsyncClient() as c:
        resp = await c.get(f"{MEMORY}/api/memory", params={"limit": 1000})
        memories = resp.json().get("memories", [])
        print(f"  Found {len(memories)} memories")
        for mem in memories:
            mem_id = mem.get("id")
            if mem_id:
                await c.delete(f"{MEMORY}/api/memory/{mem_id}")
                print(f"  Deleted memory: {mem.get('title')} (id={mem_id})")
    print("memory-tool cleared.\n")


async def clear_assets():
    print("Clearing asset-tool assets...")
    async with httpx.AsyncClient() as c:
        resp = await c.get(f"{ASSET}/api/assets", params={
            "workspace_id": "default",
            "page_size": 100,
        })
        assets = resp.json().get("data", [])
        print(f"  Found {len(assets)} assets")
        for asset in assets:
            asset_id = asset.get("id") or asset.get("asset_id")
            if asset_id:
                await c.delete(f"{ASSET}/api/assets/{asset_id}", params={
                    "workspace_id": "default",
                })
                print(f"  Deleted asset: {asset.get('name')} (id={asset_id})")
    print("asset-tool cleared.\n")


async def main():
    print("=" * 50)
    print("Clearing ALL project data from AIDP")
    print("=" * 50 + "\n")

    try:
        await clear_controller()
    except Exception as e:
        print(f"Controller error: {e}\n")

    try:
        await clear_code_index()
    except Exception as e:
        print(f"code-index error: {e}\n")

    try:
        await clear_knowledge()
    except Exception as e:
        print(f"knowledge-tool error: {e}\n")

    try:
        await clear_memory()
    except Exception as e:
        print(f"memory-tool error: {e}\n")

    try:
        await clear_assets()
    except Exception as e:
        print(f"asset-tool error: {e}\n")

    print("=" * 50)
    print("All project data cleared!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
