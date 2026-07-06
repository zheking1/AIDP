from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/templates/layouts/unified_base.html')
s = p.read_text()

# Add audit logs link after settings link
old = '''                <a href="/admin/settings" 
                   class="sidebar-item flex items-center gap-3 px-3 py-2.5 rounded-lg {% if active_page == 'settings' %}active{% endif %}">
                    <i class="fas fa-cog w-5 text-center {% if active_page == 'settings' %}text-indigo-400{% else %}text-gray-400{% endif %}"></i>
                    <span class="{% if active_page == 'settings' %}text-white font-medium{% else %}text-gray-300{% endif %}">系统设置</span>
                </a>
                {% endif %}'''

new = '''                <a href="/admin/settings" 
                   class="sidebar-item flex items-center gap-3 px-3 py-2.5 rounded-lg {% if active_page == 'settings' %}active{% endif %}">
                    <i class="fas fa-cog w-5 text-center {% if active_page == 'settings' %}text-indigo-400{% else %}text-gray-400{% endif %}"></i>
                    <span class="{% if active_page == 'settings' %}text-white font-medium{% else %}text-gray-300{% endif %}">系统设置</span>
                </a>

                <a href="/admin/audit-logs" 
                   class="sidebar-item flex items-center gap-3 px-3 py-2.5 rounded-lg {% if active_page == 'audit-logs' %}active{% endif %}">
                    <i class="fas fa-clipboard-list w-5 text-center {% if active_page == 'audit-logs' %}text-indigo-400{% else %}text-gray-400{% endif %}"></i>
                    <span class="{% if active_page == 'audit-logs' %}text-white font-medium{% else %}text-gray-300{% endif %}">审计日志</span>
                </a>
                {% endif %}'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
