import json
import requests

MCP_URL = 'http://localhost:8883/mcp/'
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/event-stream'
}

def parse_sse(text):
    for line in text.split('\n'):
        if line.startswith('data: '):
            try:
                return json.loads(line[6:])
            except:
                continue
    return None

# Step 1: Initialize session
print('=== Step 1: Initialize MCP Session ===')
r = requests.post(MCP_URL, headers=HEADERS, json={
    'jsonrpc': '2.0',
    'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05',
        'capabilities': {},
        'clientInfo': {'name': 'test-enforcement', 'version': '1.0'}
    },
    'id': 1
})
print('Status:', r.status_code)
session_id = r.headers.get('Mcp-Session-Id')
print('Session ID:', session_id)

if session_id:
    HEADERS['Mcp-Session-Id'] = session_id

# Step 2: Send initialized notification
print('\n=== Step 2: Send initialized notification ===')
r = requests.post(MCP_URL, headers=HEADERS, json={
    'jsonrpc': '2.0',
    'method': 'notifications/initialized',
    'params': {}
})
print('Status:', r.status_code)

# Step 3: Try to call invoke_tool_mcp WITHOUT aidp_context (should fail)
print('\n=== Step 3: Try invoke_tool_mcp WITHOUT aidp_context (should fail) ===')
r = requests.post(MCP_URL, headers=HEADERS, json={
    'jsonrpc': '2.0',
    'method': 'tools/call',
    'params': {
        'name': 'invoke_tool_mcp',
        'arguments': {
            'tool_name': 'memory-tool',
            'capability': 'memory.search',
            'arguments': json.dumps({'query': 'test', 'limit': 1})
        }
    },
    'id': 2
})
data = parse_sse(r.text)
if data:
    if 'error' in data:
        print('ERROR:', data['error'])
    elif 'result' in data:
        content = data['result'].get('content', [{}])[0].get('text', '')
        parsed = json.loads(content)
        if parsed.get('success') is False:
            print('BLOCKED as expected!')
            print('Error:', parsed.get('error', {}).get('message'))
        else:
            print('UNEXPECTED: Tool call succeeded without context!')
else:
    print('Response:', r.text[:200])

# Step 4: Call aidp_context (should succeed and mark session)
print('\n=== Step 4: Call aidp_context (should succeed) ===')
r = requests.post(MCP_URL, headers=HEADERS, json={
    'jsonrpc': '2.0',
    'method': 'tools/call',
    'params': {
        'name': 'aidp_context',
        'arguments': {
            'project_name': 'aidp',
            'task': 'test enforcement'
        }
    },
    'id': 3
})
data = parse_sse(r.text)
if data:
    if 'result' in data:
        content = data['result'].get('content', [{}])[0].get('text', '')
        parsed = json.loads(content)
        print('aidp_context called successfully!')
        print('Stages:', list(parsed.get('stages', {}).keys()))
    elif 'error' in data:
        print('Error:', data['error'])
else:
    print('Response:', r.text[:200])

# Step 5: Try list_registered_tools (should succeed - it's in allowed list)
print('\n=== Step 5: Try list_registered_tools (should succeed - no context needed) ===')
r = requests.post(MCP_URL, headers=HEADERS, json={
    'jsonrpc': '2.0',
    'method': 'tools/call',
    'params': {
        'name': 'list_registered_tools',
        'arguments': {}
    },
    'id': 4
})
data = parse_sse(r.text)
if data:
    if 'result' in data:
        content = data['result'].get('content', [{}])[0].get('text', '')
        parsed = json.loads(content)
        if isinstance(parsed, list):
            print('SUCCESS! Got', len(parsed), 'tools (allowed without context)')
        else:
            print('Response type:', type(parsed))
    elif 'error' in data:
        print('Error:', data['error'])
else:
    print('Response:', r.text[:200])

# Step 6: Test memory search (should also succeed)
print('\n=== Step 6: Test memory search (should succeed) ===')
r = requests.post(MCP_URL, headers=HEADERS, json={
    'jsonrpc': '2.0',
    'method': 'tools/call',
    'params': {
        'name': 'invoke_tool_mcp',
        'arguments': {
            'tool_name': 'memory-tool',
            'capability': 'memory.search',
            'arguments': json.dumps({'query': 'test', 'limit': 2})
        }
    },
    'id': 5
})
data = parse_sse(r.text)
if data:
    if 'result' in data:
        content = data['result'].get('content', [{}])[0].get('text', '')
        parsed = json.loads(content)
        if parsed.get('success'):
            print('SUCCESS! Memory search worked')
            print('Results:', len(parsed.get('results', [])), 'items')
        elif parsed.get('success') is False:
            print('BLOCKED!')
            print('Error:', parsed.get('error'))
    elif 'error' in data:
        print('Error:', data['error'])
else:
    print('Response:', r.text[:200])

print('\n=== ENFORCEMENT TEST COMPLETE ===')
