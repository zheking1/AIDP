import subprocess, os, re

base = r"D:\Project\openCode\apps\controller\app\web\templates\modules"
files = [
    "skills/personal_content.html",
    "skills/global_content.html", 
    "rules/global_content.html",
    "rules/personal_content.html",
    "agents/list_content.html",
    "assets/list_content.html",
    "sandbox/index_content.html",
    "workflows/list_content.html",
]

for f in files:
    nas_path = f.replace('\\', '/')
    cmd = f'ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker exec aidp-controller cat /app/app/web/templates/modules/{nas_path}"'
    result = subprocess.run(cmd, capture_output=True, shell=True)
    raw = result.stdout
    
    if raw[:2] == b'\xff\xfe':
        content = raw.decode('utf-16-le')
    elif raw[:2] == b'\xfe\xff':
        content = raw.decode('utf-16-be')
    elif raw[:3] == b'\xef\xbb\xbf':
        content = raw.decode('utf-8-sig')
    else:
        content = raw.decode('utf-8')
    
    new_content = content
    
    # Fix 1: close title div before buttons div
    # Remove the blank line and add </div> before buttons div
    p1 = re.compile(r'(<div>\s*<h1[^>]*>.*?</h1>\s*<p[^>]*>.*?</p>\s*)\n\s*\n(\s*<div class="flex)', re.DOTALL)
    new_content = p1.sub(r'\1\n      </div>\n\2', new_content, count=1)
    
    # Fix 2: add flex class to header wrapper AND add closing </div> for it
    # Find: <div>  (header wrapper, after <!-- Header -->\n)
    # Followed by: \n      <div>\n<h1>...</h1>\n<p>...</p>\n      </div>\n      <div class="flex...\n    </div>
    # Add class to <div> and add another </div> after the last </div>
    
    p2 = re.compile(r'(<!-- Header -->\s*)<div>(\s*<div>\s*<h1[^>]*>.*?</h1>\s*<p[^>]*>.*?</p>\s*</div>\s*<div class="flex.*?</div>)\s*\n', re.DOTALL)
    
    def fixer(m):
        header_comment = m.group(1)
        inner = m.group(2)
        return header_comment + '<div class="flex items-center justify-between">' + inner + '\n</div>\n'
    
    new_content = p2.sub(fixer, new_content, count=1)
    
    path = os.path.join(base, f)
    with open(path, 'wb') as fh:
        fh.write(new_content.encode('utf-8'))
    
    changed = (new_content != content)
    print(f"{f}: {'fixed' if changed else 'no-change'}")