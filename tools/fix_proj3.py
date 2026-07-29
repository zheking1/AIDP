with open('/app/app/routers/projects_new.py', encoding='utf-8') as f:
    c = f.read()

c = c.replace('        tech_stack=json.dumps(data.tech_stack)', '')
c = c.replace("    tech_stack: List[str] = Field(default_factory=list, description='技术栈标签')", '')
c = c.replace('    tech_stack: Optional[List[str]] = None', '')
c = c.replace('    tech_stack: List[str]', '')

with open('/app/app/routers/projects_new.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')