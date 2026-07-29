"""Fix corrupted Chinese characters in projects_new.py"""
import re

with open("D:/Project/openCode/apps/controller/app/routers/projects_new.py", encoding="utf-8") as f:
    text = f.read()

# Remove all corrupted Chinese (characters outside ASCII range that are garbled)
# Keep only ASCII and valid Python syntax
import unicodedata

clean = []
for ch in text:
    if ord(ch) < 128 or ch in '"""\n \t':
        clean.append(ch)
    elif ch in "'\u2018\u2019":
        clean.append("'")
    else:
        # Replace non-ASCII with space (comments will lose Chinese but code stays)
        clean.append(" ")

text = "".join(clean)

# Clean up multiple spaces
text = re.sub(r' {2,}', ' ', text)

with open("D:/Project/openCode/apps/controller/app/routers/projects_new.py", "w", encoding="utf-8") as f:
    f.write(text)

import ast
try:
    ast.parse(text)
    print("File is valid Python")
except SyntaxError as e:
    print(f"Still has syntax error at line {e.lineno}: {e.msg}")