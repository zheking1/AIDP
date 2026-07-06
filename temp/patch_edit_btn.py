from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/templates/admin/users.html')
s = p.read_text()

# Add edit button before delete button
old = '''                                    <button @click="confirmDelete(user)" 
                                            class="p-1.5 rounded-lg text-red-400 hover:bg-red-500/20 text-sm transition"
                                            title="删除">
                                        <i class="fas fa-trash"></i>
                                    </button>'''

new = '''                                    <a :href="'/admin/users/' + user.id + '/edit'"
                                       class="p-1.5 rounded-lg text-blue-400 hover:bg-blue-500/20 text-sm transition"
                                       title="编辑">
                                        <i class="fas fa-edit"></i>
                                    </a>
                                    <button @click="confirmDelete(user)" 
                                            class="p-1.5 rounded-lg text-red-400 hover:bg-red-500/20 text-sm transition"
                                            title="删除">
                                        <i class="fas fa-trash"></i>
                                    </button>'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
