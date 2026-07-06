from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/templates/admin/users.html')
s = p.read_text()

# Make username a link to detail page
old = '''                                        <p class="text-sm font-medium text-white" x-text="user.username"></p>'''

new = '''                                        <a :href="'/admin/users/' + user.id" class="text-sm font-medium text-white hover:text-indigo-400 transition" x-text="user.username"></a>'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
