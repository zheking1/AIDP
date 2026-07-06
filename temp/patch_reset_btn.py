from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/templates/admin/user_detail.html')
s = p.read_text()

# Add reset password button after edit button
old = '''                    <a :href="'/admin/users/' + userId + '/edit'"
                       class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg transition">
                        <i class="fas fa-edit mr-1"></i>编辑
                    </a>'''

new = '''                    <a :href="'/admin/users/' + userId + '/edit'"
                       class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg transition">
                        <i class="fas fa-edit mr-1"></i>编辑
                    </a>
                    <button @click="showResetModal = true"
                            class="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded-lg transition">
                        <i class="fas fa-key mr-1"></i>重置密码
                    </button>'''

s = s.replace(old, new)

# Add reset password modal before closing div
old = '''</div>

{% endblock %}'''

new = '''    <!-- Reset Password Modal -->
    <div x-show="showResetModal" x-cloak x-transition class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60" @click="showResetModal = false"></div>
        <div class="relative bg-gray-800 rounded-xl border border-gray-700 p-6 w-full max-w-md shadow-2xl">
            <h3 class="text-lg font-bold text-white mb-2">重置密码</h3>
            <p class="text-gray-400 text-sm mb-4">
                为用户 <span class="text-white font-medium" x-text="user?.username"></span> 设置新密码
            </p>
            <input type="password" x-model="newPassword"
                   class="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-sm text-white
                          placeholder-gray-400 focus:outline-none focus:border-indigo-500 mb-4"
                   placeholder="新密码（至少 6 个字符）">
            <p x-show="resetError" class="text-red-400 text-sm mb-4" x-text="resetError"></p>
            <div class="flex justify-end gap-3">
                <button @click="showResetModal = false; newPassword = ''; resetError = ''"
                        class="px-4 py-2 text-sm text-gray-300 hover:text-white transition">
                    取消
                </button>
                <button @click="resetPassword()" :disabled="resetting"
                        class="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded-lg transition disabled:opacity-50">
                    <span x-text="resetting ? '重置中...' : '确认重置'"></span>
                </button>
            </div>
        </div>
    </div>
</div>

{% endblock %}'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
