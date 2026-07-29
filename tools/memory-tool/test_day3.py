import httpx
import asyncio

async def test_day3():
    base_url = "http://localhost:18085"
    
    print("=== Day 3 Tests ===\n")
    
    async with httpx.AsyncClient() as client:
        # Test 1: Graph API
        print("1. Graph Data API")
        resp = await client.get(f"{base_url}/api/memories/graph/data")
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json().get('data', {})
            print(f"   Nodes: {data.get('total_nodes', 0)}")
            print(f"   Links: {data.get('total_links', 0)}")
        print()
        
        # Test 2: Search API
        print("2. Vector Search API")
        resp = await client.post(
            f"{base_url}/api/memories/search/vector",
            json={"query": "test", "top_k": 5}
        )
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json().get('data', {})
            print(f"   Results: {data.get('total', 0)}")
            print(f"   Type: {data.get('search_type', 'unknown')}")
        print()
        
        # Test 3: Stats API
        print("3. Stats API")
        resp = await client.get(f"{base_url}/api/memories/stats/overview")
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json().get('data', {})
            print(f"   Total Memories: {data.get('total_memories', 0)}")
            print(f"   Total Relations: {data.get('total_relations', 0)}")
        print()
        
        # Test 4: Web UI
        print("4. Web UI Pages")
        for path in ["/memories", "/memories/graph"]:
            resp = await client.get(f"{base_url}{path}")
            print(f"   {path}: {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(test_day3())