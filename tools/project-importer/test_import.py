import httpx
import json

async def test_import():
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            'http://localhost:18090/api/onboarding/import',
            json={
                'path': '/tmp/test-project',
                'name': 'test-tech-import',
                'type': 'java',
                'auto_import_docs': True
            }
        )
        print(f'Status: {resp.status_code}')
        print(json.dumps(resp.json(), indent=2))

if __name__ == '__main__':
    import asyncio
    asyncio.run(test_import())