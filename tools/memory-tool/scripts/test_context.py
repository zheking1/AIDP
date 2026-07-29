#!/usr/bin/env python3
"""
Test context package generation end-to-end
"""
import asyncio
import json
import random
from typing import List, Dict

import httpx

BASE_URL = "http://192.168.0.100:18085"


async def get_memories(client: httpx.AsyncClient) -> List[Dict]:
    """Fetch all memories"""
    memories = []
    page = 1
    
    while True:
        resp = await client.get(f"{BASE_URL}/api/memories?page={page}&page_size=50")
        if resp.status_code == 200:
            result = resp.json()
            items = result.get("data", {}).get("items", [])
            memories.extend(items)
            
            total_pages = result.get("data", {}).get("pages", 1)
            if page >= total_pages:
                break
            page += 1
        else:
            break
    
    return memories


async def test_preview_generation(client: httpx.AsyncClient, memories: List[Dict]):
    """Test context preview generation"""
    print("\n" + "-" * 50)
    print("Test 1: Context Preview Generation")
    print("-" * 50)
    
    if len(memories) < 2:
        print("[SKIP] Not enough memories for test")
        return
    
    # Select random memories
    selected = random.sample(memories, min(5, len(memories)))
    memory_ids = [m["id"] for m in selected]
    
    data = {
        "memory_ids": memory_ids,
        "format": "markdown",
        "max_tokens": 2000,
    }
    
    try:
        resp = await client.post(f"{BASE_URL}/api/context-packages/preview", json=data)
        if resp.status_code in (200, 201):
            result = resp.json()
            preview_data = result.get("data", {})
            print(f"[OK] Preview generated")
            print(f"     Memories: {len(memory_ids)}")
            print(f"     Estimated tokens: {preview_data.get('estimated_tokens', 0)}")
            print(f"     Actual tokens: {preview_data.get('actual_tokens', 0)}")
            print(f"     Content length: {len(preview_data.get('content', ''))} chars")
            print(f"\nPreview excerpt:")
            content = preview_data.get("content", "")
            print(content[:300] + "..." if len(content) > 300 else content)
            return True
        else:
            print(f"[ERR] Failed: {resp.status_code}")
            print(f"      {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[ERR] Error: {e}")
        return False


async def test_context_package_crud(client: httpx.AsyncClient, memories: List[Dict]):
    """Test context package CRUD operations"""
    print("\n" + "-" * 50)
    print("Test 2: Context Package CRUD")
    print("-" * 50)
    
    if len(memories) < 3:
        print("[SKIP] Not enough memories for test")
        return
    
    # Create
    selected = random.sample(memories, 3)
    memory_ids = [m["id"] for m in selected]
    
    create_data = {
        "name": "Test Context Package",
        "description": "Auto-generated test package",
        "memory_ids": memory_ids,
        "format": "markdown",
        "max_tokens": 1500,
    }
    
    package_id = None
    try:
        resp = await client.post(f"{BASE_URL}/api/context-packages", json=create_data)
        if resp.status_code in (200, 201):
            result = resp.json()
            package_data = result.get("data", {})
            package_id = package_data.get("id")
            print(f"[OK] Created package: {package_id}")
            print(f"     Name: {package_data.get('name')}")
            print(f"     Memories: {len(package_data.get('memory_ids', []))}")
            print(f"     Tokens: {package_data.get('actual_tokens', 0)}")
        else:
            print(f"[ERR] Create failed: {resp.status_code}")
            print(f"      {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[ERR] Create error: {e}")
        return False
    
    # Read
    if package_id:
        try:
            resp = await client.get(f"{BASE_URL}/api/context-packages/{package_id}")
            if resp.status_code == 200:
                result = resp.json()
                print(f"[OK] Read package: {result['data']['name']}")
            else:
                print(f"[ERR] Read failed: {resp.status_code}")
        except Exception as e:
            print(f"[ERR] Read error: {e}")
    
    # List
    try:
        resp = await client.get(f"{BASE_URL}/api/context-packages")
        if resp.status_code == 200:
            result = resp.json()
            items = result.get("data", {}).get("items", [])
            print(f"[OK] Listed packages: {len(items)} total")
        else:
            print(f"[ERR] List failed: {resp.status_code}")
    except Exception as e:
        print(f"[ERR] List error: {e}")
    
    # Update
    if package_id:
        try:
            update_data = {
                "name": "Updated Test Package",
                "description": "Updated description",
                "memory_ids": memory_ids[:2],  # Remove one memory
                "format": "json",
                "max_tokens": 1000,
            }
            resp = await client.put(f"{BASE_URL}/api/context-packages/{package_id}", json=update_data)
            if resp.status_code == 200:
                result = resp.json()
                print(f"[OK] Updated package: {result['data']['name']}")
                print(f"     New format: {result['data']['format']}")
            else:
                print(f"[ERR] Update failed: {resp.status_code}")
        except Exception as e:
            print(f"[ERR] Update error: {e}")
    
    # Delete
    if package_id:
        try:
            resp = await client.delete(f"{BASE_URL}/api/context-packages/{package_id}")
            if resp.status_code == 200:
                print(f"[OK] Deleted package: {package_id}")
            else:
                print(f"[ERR] Delete failed: {resp.status_code}")
        except Exception as e:
            print(f"[ERR] Delete error: {e}")
    
    return True


async def test_generate_context(client: httpx.AsyncClient, memories: List[Dict]):
    """Test auto-generate context from query"""
    print("\n" + "-" * 50)
    print("Test 3: Auto-generate Context from Query")
    print("-" * 50)
    
    queries = [
        "数据库设计",
        "API架构",
        "性能优化",
        "前端框架",
    ]
    
    for query in queries:
        data = {
            "query": query,
            "max_tokens": 1000,
            "format": "markdown",
            "top_k": 3,
        }
        
        try:
            resp = await client.post(f"{BASE_URL}/api/context-packages/generate", json=data)
            if resp.status_code in (200, 201):
                result = resp.json()
                gen_data = result.get("data", {})
                print(f"[OK] Query: '{query}'")
                print(f"     Found {len(gen_data.get('memory_ids', []))} relevant memories")
                print(f"     Tokens: {gen_data.get('actual_tokens', 0)}")
                print(f"     Content preview: {gen_data.get('content', '')[:100]}...")
                print()
            else:
                print(f"[ERR] Query '{query}' failed: {resp.status_code}")
        except Exception as e:
            print(f"[ERR] Query '{query}' error: {e}")
    
    return True


async def main():
    """Main test function"""
    print("=" * 60)
    print("Context Package E2E Test")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Health check
        try:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code != 200:
                print("[ERR] Memory tool not responding")
                return
            print("[OK] Memory tool is healthy")
        except Exception as e:
            print(f"[ERR] Cannot connect: {e}")
            return
        
        # Get memories
        print("\nFetching memories...")
        memories = await get_memories(client)
        print(f"Found {len(memories)} memories")
        
        if len(memories) < 2:
            print("Need at least 2 memories for testing")
            return
        
        # Run tests
        results = []
        results.append(("Preview Generation", await test_preview_generation(client, memories)))
        results.append(("Package CRUD", await test_context_package_crud(client, memories)))
        results.append(("Auto-generate", await test_generate_context(client, memories)))
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        for name, passed in results:
            status = "PASS" if passed else "FAIL"
            color = "✓" if passed else "✗"
            print(f"{color} {name}: {status}")


if __name__ == "__main__":
    asyncio.run(main())
