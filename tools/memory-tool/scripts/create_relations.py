#!/usr/bin/env python3
"""
Create relations between existing memories
"""
import asyncio
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


async def create_relations(client: httpx.AsyncClient, memories: List[Dict]):
    """Create relations between memories"""
    # Group by category
    by_category = {}
    for mem in memories:
        cat = mem.get("category", "unknown")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(mem)
    
    # Create relations within same category
    relations_created = 0
    relation_types = ["related", "depends_on", "similar_to", "supersedes"]
    
    for cat, mems in by_category.items():
        if len(mems) >= 2:
            # Create chain relations
            for i in range(len(mems) - 1):
                source = mems[i]
                target = mems[i + 1]
                
                relation_data = {
                    "source_id": source["id"],
                    "target_id": target["id"],
                    "relation_type": "related",
                    "strength": round(random.uniform(0.5, 1.0), 2),
                }
                
                try:
                    resp = await client.post(f"{BASE_URL}/api/relations", json=relation_data)
                    if resp.status_code in (200, 201):
                        relations_created += 1
                        print(f"[OK] Relation: {source['title'][:30]}... -> {target['title'][:30]}...")
                except Exception as e:
                    print(f"[ERR] Relation error: {e}")
            
            # Create some random additional relations
            if len(mems) >= 3:
                for _ in range(min(2, len(mems) - 2)):
                    pair = random.sample(mems, 2)
                    relation_data = {
                        "source_id": pair[0]["id"],
                        "target_id": pair[1]["id"],
                        "relation_type": random.choice(relation_types),
                        "strength": round(random.uniform(0.3, 0.9), 2),
                    }
                    try:
                        resp = await client.post(f"{BASE_URL}/api/memories/relations", json=relation_data)
                        if resp.status_code in (200, 201):
                            relations_created += 1
                            print(f"[OK] Extra relation: {pair[0]['title'][:25]}... -> {pair[1]['title'][:25]}...")
                    except:
                        pass
    
    # Create cross-category relations
    categories = list(by_category.keys())
    for _ in range(min(8, len(categories) * 2)):
        if len(categories) >= 2:
            cat1, cat2 = random.sample(categories, 2)
            if by_category[cat1] and by_category[cat2]:
                source = random.choice(by_category[cat1])
                target = random.choice(by_category[cat2])
                
                relation_data = {
                    "source_id": source["id"],
                    "target_id": target["id"],
                    "relation_type": random.choice(["depends_on", "related"]),
                    "strength": round(random.uniform(0.3, 0.8), 2),
                }
                
                try:
                    resp = await client.post(f"{BASE_URL}/api/relations", json=relation_data)
                    if resp.status_code in (200, 201):
                        relations_created += 1
                        print(f"[OK] Cross: {source['title'][:20]}... -> {target['title'][:20]}...")
                except:
                    pass
    
    return relations_created


async def create_context_packages(client: httpx.AsyncClient, memories: List[Dict]):
    """Create sample context packages"""
    # Group memories by category
    by_category = {}
    for mem in memories:
        cat = mem.get("category", "unknown")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(mem["id"])
    
    contexts_to_create = [
        ("Architecture Knowledge", ["pattern", "decision", "architecture"]),
        ("Bug Fix Playbook", ["bug", "issue"]),
        ("Development Setup", ["other", "architecture"]),
        ("All Patterns", ["pattern", "issue"]),
    ]
    
    created = 0
    for ctx_name, categories in contexts_to_create:
        memory_ids = []
        for cat in categories:
            if cat in by_category:
                memory_ids.extend(by_category[cat][:4])
        
        if len(memory_ids) < 2:
            continue
        
        data = {
            "name": ctx_name,
            "description": f"Context package with {len(memory_ids)} related memories",
            "memory_ids": memory_ids[:10],
            "format": "markdown",
            "max_tokens": random.choice([1500, 2000, 2500]),
        }
        
        try:
            resp = await client.post(f"{BASE_URL}/api/context-packages", json=data)
            if resp.status_code in (200, 201):
                result = resp.json()
                pkg = result.get("data", result)
                print(f"[OK] Context: {ctx_name} ({len(memory_ids)} memories, {pkg.get('actual_tokens', 0)} tokens)")
                created += 1
            else:
                print(f"[ERR] Failed context: {ctx_name} - {resp.status_code}")
        except Exception as e:
            print(f"[ERR] Error context: {ctx_name} - {e}")
    
    return created


async def main():
    """Main function"""
    print("=" * 60)
    print("Memory Tool Relations & Context Generator")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check health
        try:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code != 200:
                print("[ERR] Memory tool not responding")
                return
            print("[OK] Memory tool is healthy")
        except Exception as e:
            print(f"[ERR] Cannot connect: {e}")
            return
        
        # Get existing memories
        print("\nFetching existing memories...")
        memories = await get_memories(client)
        print(f"Found {len(memories)} memories")
        
        if len(memories) < 2:
            print("Need at least 2 memories to create relations")
            return
        
        # Create relations
        print("\n" + "-" * 40)
        print("Creating relations...")
        print("-" * 40)
        relations = await create_relations(client, memories)
        print(f"\nTotal relations created: {relations}")
        
        # Create context packages
        print("\n" + "-" * 40)
        print("Creating context packages...")
        print("-" * 40)
        contexts = await create_context_packages(client, memories)
        print(f"\nTotal context packages created: {contexts}")
        
        print("\n" + "=" * 60)
        print("Done! Access the web UI at:")
        print(f"  - Memories: {BASE_URL}/memories")
        print(f"  - Graph: {BASE_URL}/memories/graph")
        print(f"  - Context: {BASE_URL}/context")


if __name__ == "__main__":
    asyncio.run(main())
