import subprocess, sys

script = r'''from jinja2 import Environment, FileSystemLoader
import os

templates_dir = '/app/app/web/templates'
env = Environment(loader=FileSystemLoader(templates_dir))

test_files = [
    'modules/memory/memories.html',
    'modules/memory/memories_content.html',
    'modules/skills/global_content.html',
    'modules/knowledge/bases_content.html',
    'admin/users-frame_content.html',
]

for name in test_files:
    try:
        t = env.get_template(name)
        print(f'OK: {name}')
    except Exception as e:
        print(f'FAIL: {name} -> {e}')
'''

# Write to a temp file
with open(r'D:\Project\openCode\tools\check_jinja.py', 'w', encoding='utf-8') as f:
    f.write(script)

# Copy to NAS
subprocess.run([
    'scp', '-i', '~/.ssh/nas_temp',
    r'D:\Project\openCode\tools\check_jinja.py',
    'root@192.168.0.100:/tmp/check_jinja.py'
], shell=True)

# Execute in container
result = subprocess.run([
    'ssh', '-i', '~/.ssh/nas_temp', 'root@192.168.0.100',
    'docker cp /tmp/check_jinja.py aidp-controller:/tmp/check_jinja.py && docker exec aidp-controller python3 /tmp/check_jinja.py'
], capture_output=True, shell=True, text=True)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr[:500])