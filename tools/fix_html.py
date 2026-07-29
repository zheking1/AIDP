import os, re, codecs

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
    path = os.path.join(base, f)
    # Detect BOM
    with open(path, 'rb') as fh:
        raw = fh.read()
    
    if raw[:2] == b'\xff\xfe':
        encoding = 'utf-16-le'
    elif raw[:2] == b'\xfe\xff':
        encoding = 'utf-16-be'
    elif raw[:3] == b'\xef\xbb\xbf':
        encoding = 'utf-8-sig'
    else:
        encoding = 'utf-8'
    
    content = raw.decode(encoding)
    
    # Fix pattern: title div missing closing </div> before buttons div
    pattern = r'(<div>\s*<h1[^>]*>.*?</h1>\s*<p[^>]*>.*?</p>\s*)\n(?:\s*\n)?(\s*<div class="flex)'
    replacement = r'\1\n      </div>\n\2'
    
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    
    if new_content != content:
        with open(path, 'wb') as fh:
            fh.write(new_content.encode('utf-8'))
        print(f"Fixed: {f}")
    else:
        print(f"No change: {f}")