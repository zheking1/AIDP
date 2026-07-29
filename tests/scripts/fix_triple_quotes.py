with open("D:/Project/openCode/apps/controller/app/routers/projects_new.py") as f:
    text = f.read()
text = text.replace('"""\n        ', '# ')
text = text.replace('"""\n    ', '# ')
text = text.replace('"""', '')
with open("D:/Project/openCode/apps/controller/app/routers/projects_new.py", "w") as f:
    f.write(text)
import ast
try:
    ast.parse(text)
    print("OK")
except SyntaxError as e:
    print(f"Line {e.lineno}: {e.msg}")