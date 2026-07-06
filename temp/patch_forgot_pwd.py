from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/templates/auth/login.html')
s = p.read_text()

# Add forgot password link after register link
old = '''            <!-- Register Link -->
            <div class="mt-4 text-center">
                <p class="text-sm text-gray-400">
                    还没有账号？
                    <a href="/register" class="text-indigo-400 hover:text-indigo-300 font-medium">立即注册</a>
                </p>
            </div>'''

new = '''            <!-- Register Link -->
            <div class="mt-4 text-center">
                <p class="text-sm text-gray-400">
                    还没有账号？
                    <a href="/register" class="text-indigo-400 hover:text-indigo-300 font-medium">立即注册</a>
                </p>
                <p class="text-sm text-gray-400 mt-2">
                    忘记密码？请联系管理员重置
                </p>
            </div>'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
