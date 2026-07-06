from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/templates/auth/login.html')
s = p.read_text()

# Add register link after default credentials hint
old = '''            <!-- Default Credentials Hint -->
            <div class="mt-6 p-4 bg-gray-700/50 rounded-lg border border-gray-600">
                <p class="text-xs text-gray-400 text-center">
                    默认管理员账号：<br>
                    <span class="text-gray-300">用户名：admin</span> | 
                    <span class="text-gray-300">密码：admin123</span>
                </p>
            </div>
        </div>'''

new = '''            <!-- Default Credentials Hint -->
            <div class="mt-6 p-4 bg-gray-700/50 rounded-lg border border-gray-600">
                <p class="text-xs text-gray-400 text-center">
                    默认管理员账号：<br>
                    <span class="text-gray-300">用户名：admin</span> | 
                    <span class="text-gray-300">密码：admin123</span>
                </p>
            </div>

            <!-- Register Link -->
            <div class="mt-4 text-center">
                <p class="text-sm text-gray-400">
                    还没有账号？
                    <a href="/register" class="text-indigo-400 hover:text-indigo-300 font-medium">立即注册</a>
                </p>
            </div>
        </div>'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
