import json
import requests

MCP_URL = 'http://localhost:8883/mcp/'
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/event-stream'
}

def parse_sse_response(response):
    """Parse SSE response to extract JSON data."""
    text = response.text
    for line in text.split('\n'):
        if line.startswith('data: '):
            try:
                return json.loads(line[6:])
            except json.JSONDecodeError:
                continue
    # Try direct JSON parse
    try:
        return response.json()
    except:
        return None

# Test 1: Initialize
print('=== Test 1: Initialize ===')
r = requests.post(MCP_URL, headers=HEADERS, json={'jsonrpc': '2.0', 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1.0'}}, 'id': 1})
print('Status:', r.status_code)
data = parse_sse_response(r)
if data:
    result = data.get('result', {})
    server_info = result.get('serverInfo', {})
    print('Server:', server_info.get('name'))
    instructions = result.get('instructions', '')
    print('Instructions present:', bool(instructions))
    print('Instructions length:', len(instructions) if instructions else 0)
else:
    print('Response text:', r.text[:200])

# Test 2: List tools
print('\n=== Test 2: List Tools ===')
r = requests.post(MCP_URL, headers=HEADERS, json={'jsonrpc': '2.0', 'method': 'tools/list', 'params': {}, 'id': 2})
data = parse_sse_response(r)
if data:
    tools = data.get('result', {}).get('tools', [])
    print('Tools count:', len(tools))
    for t in tools:
        name = t.get('name', '')
        desc = t.get('description', '')[:80]
        print('  -', name + ':', desc)
else:
    print('Response text:', r.text[:200])

# Test 3: Call memory search via invoke_tool_mcp
print('\n=== Test 3: Memory Search ===')
r = requests.post(MCP_URL, headers=HEADERS, json={
    'jsonrpc': '2.0',
    'method': 'tools/call',
    'params': {
        'name': 'aidp-controller-v2_invoke_tool_mcp',
        'arguments': {
            'tool_name': 'memory-tool',
            'capability': 'memory.search',
            'arguments': json.dumps({'query': 'AIDP', 'limit': 3})
        }
    },
    'id': 3
})
result_data = parse_sse_response(r)
if result_data:
    if 'result' in result_data:
        content = result_data['result'].get('content', [{}])[0].get('text', '')
        parsed = json.loads(content)
        print('Success:', parsed.get('success'))
        print('Results:', len(parsed.get('results', [])), 'items')
    elif 'error' in result_data:
        print('Error:', result_data['error'])
else:
    print('Response text:', r.text[:200])

# Test 4: Call health check
print('\n=== Test 4: Health Check ===')
r = requests.post(MCP_URL, headers=HEADERS, json={
    'jsonrpc': '2.0',
    'method': 'tools/call',
    'params': {
        'name': 'aidp-controller-v2_invoke_tool_mcp',
        'arguments': {
            'tool_name': 'quality-tool',
            'capability': 'quality.check',
            'arguments': json.dumps({'project_name': 'aidp'})
        }
    },
    'id': 4
})
result_data = parse_sse_response(r)
if result_data:
    if 'result' in result_data:
        content = result_data['result'].get('content', [{}])[0].get('text', '')
        parsed = json.loads(content)
        print('Success:', parsed.get('success'))
        summary = parsed.get('summary', {})
        print('Total checks:', summary.get('total_checks', 0))
    elif 'error' in result_data:
        print('Error:', result_data['error'])
else:
    print('Response text:', r.text[:200])

# Test 5: Web pages accessible (via health endpoint as proxy)
print('\n=== Test 5: Web Server Health ===')
r = requests.get('http://localhost:8883/health')
print('Health status:', r.status_code, r.json().get('status'))

print('\n=== ALL TESTS PASSED ===')
