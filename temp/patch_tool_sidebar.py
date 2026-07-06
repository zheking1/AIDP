from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/templates/layouts/unified_base.html')
s = p.read_text()

# Add tools admin link after models link
old = '''                <a href="/admin/settings"'''

new = '''                <a href="/admin/tools" 
                   class="sidebar-item flex items-center gap-3 px-3 py-2.5 rounded-lg {% if active_page == 'tools-admin' %}active{% endif %}">
                    <i class="fas fa-plug w-5 text-center {% if active_page == 'tools-admin' %}text-indigo-400{% else %}text-gray-400{% endif %}"></i>
                    <span class="{% if active_page == 'tools-admin' %}text-white font-medium{% else %}text-gray-300{% endif %}">工具管理</span>
                </a>
                
                <a href="/admin/settings"'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
