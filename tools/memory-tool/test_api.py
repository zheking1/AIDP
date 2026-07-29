import httpx
import asyncio

async def test_apis():
    base_url = "http://localhost:18085"
    
    # Test 1: Health
    print("=== Test 1: Health Check ===")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base_url}/health")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    
    # Test 2: Create Memory
    print("\n=== Test 2: Create Memory ===")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base_url}/api/memories",
            json={
                "title": "Test API Memory",
                "content": "This is a test memory created via the new API",
                "category": "pattern",
                "project": "test-project"
            }
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text[:500]}")
        
        if resp.status_code == 201:
            data = resp.json()
            memory_id = data.get("data", {}).get("id")
            
            # Test 3: List Memories
            print("\n=== Test 3: List Memories ===")
            resp = await client.get(f"{base_url}/api/memories")
            print(f"Status: {resp.status_code}")
            print(f"Total: {resp.json().get('data', {}).get('total', 0)}")
            
            # Test 4: Get Memory Detail
            if memory_id:
                print(f"\n=== Test 4: Get Memory {memory_id} ===")
                resp = await client.get(f"{base_url}/api/memories/{memory_id}")
                print(f"Status: {resp.status_code}")
                print(f"Title: {resp.json().get('data', {}).get('title')}")
            
            # Test 5: Graph Data
            print("\n=== Test 5: Graph Data ===")
            resp = await client.get(f"{base_url}/api/memories/graph/data")
            print(f"Status: {resp.status_code}")
            data = resp.json().get("data", {})
            print(f"Nodes: {data.get('total_nodes', 0)}")
            print(f"Links: {data.get('total_links', 0)}")

if __name__ == "__main__":
    asyncio.run(test_apis())