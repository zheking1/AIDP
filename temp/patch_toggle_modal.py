from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/templates/admin/users.html')
s = p.read_text()

# Add toggle confirmation modal after delete modal
old_modal = '''    <!-- Delete Confirmation Modal -->
    <div x-show="showDeleteModal" x-cloak x-transition class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60" @click="showDeleteModal = false"></div>
        <div class="relative bg-gray-800 rounded-xl border border-gray-700 p-6 w-full max-w-md shadow-2xl">
            <h3 class="text-lg font-bold text-white mb-2">确认删除</h3>
            <p class="text-gray-400 text-sm mb-6">
                确定要删除用户 <span class="text-white font-medium" x-text="deleteTarget?.username"></span> 吗？此操作不可撤销。
            </p>
            <div class="flex justify-end gap-3">
                <button @click="showDeleteModal = false"
                        class="px-4 py-2 text-sm text-gray-300 hover:text-white transition">
                    取消
                </button>
                <button @click="deleteUser()" 
                        class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg transition">
                    确认删除
                </button>
            </div>
        </div>
    </div>'''

new_modal = '''    <!-- Toggle Confirmation Modal -->
    <div x-show="showToggleModal" x-cloak x-transition class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60" @click="showToggleModal = false"></div>
        <div class="relative bg-gray-800 rounded-xl border border-gray-700 p-6 w-full max-w-md shadow-2xl">
            <h3 class="text-lg font-bold text-white mb-2" x-text="toggleTarget?.status === 'active' ? '确认禁用' : '确认启用'"></h3>
            <p class="text-gray-400 text-sm mb-6">
                确定要<span x-text="toggleTarget?.status === 'active' ? '禁用' : '启用'"></span>用户 
                <span class="text-white font-medium" x-text="toggleTarget?.username"></span> 吗？
            </p>
            <div class="flex justify-end gap-3">
                <button @click="showToggleModal = false"
                        class="px-4 py-2 text-sm text-gray-300 hover:text-white transition">
                    取消
                </button>
                <button @click="doToggle()" 
                        class="px-4 py-2 text-white text-sm rounded-lg transition"
                        :class="toggleTarget?.status === 'active' ? 'bg-yellow-600 hover:bg-yellow-700' : 'bg-green-600 hover:bg-green-700'">
                    确认
                </button>
            </div>
        </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div x-show="showDeleteModal" x-cloak x-transition class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60" @click="showDeleteModal = false"></div>
        <div class="relative bg-gray-800 rounded-xl border border-gray-700 p-6 w-full max-w-md shadow-2xl">
            <h3 class="text-lg font-bold text-white mb-2">确认删除</h3>
            <p class="text-gray-400 text-sm mb-6">
                确定要删除用户 <span class="text-white font-medium" x-text="deleteTarget?.username"></span> 吗？此操作不可撤销。
            </p>
            <div class="flex justify-end gap-3">
                <button @click="showDeleteModal = false"
                        class="px-4 py-2 text-sm text-gray-300 hover:text-white transition">
                    取消
                </button>
                <button @click="deleteUser()" 
                        class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg transition">
                    确认删除
                </button>
            </div>
        </div>
    </div>'''

s = s.replace(old_modal, new_modal)

# Update the toggle button to show modal instead of direct action
old_toggle = '''                                    <button @click="toggleUser(user)" 
                                            class="p-1.5 rounded-lg text-sm transition"
                                            :class="user.status === 'active' ? 'text-yellow-400 hover:bg-yellow-500/20' : 'text-green-400 hover:bg-green-500/20'"
                                            :title="user.status === 'active' ? '禁用' : '启用'">
                                        <i :class="user.status === 'active' ? 'fas fa-ban' : 'fas fa-check'"></i>
                                    </button>'''

new_toggle = '''                                    <button @click="confirmToggle(user)" 
                                            class="p-1.5 rounded-lg text-sm transition"
                                            :class="user.status === 'active' ? 'text-yellow-400 hover:bg-yellow-500/20' : 'text-green-400 hover:bg-green-500/20'"
                                            :title="user.status === 'active' ? '禁用' : '启用'">
                                        <i :class="user.status === 'active' ? 'fas fa-ban' : 'fas fa-check'"></i>
                                    </button>'''

s = s.replace(old_toggle, new_toggle)

# Add state and functions for toggle modal
old_state = '''        showDeleteModal: false,
        deleteTarget: null,
        editingRemark: null,'''

new_state = '''        showDeleteModal: false,
        deleteTarget: null,
        showToggleModal: false,
        toggleTarget: null,
        editingRemark: null,'''

s = s.replace(old_state, new_state)

# Replace toggleUser function and add confirmToggle and doToggle
old_toggle_fn = '''        async toggleUser(user) {
            try {
                const resp = await fetch(`/api/auth/users/${user.id}/toggle`, { method: 'POST' });
                const data = await resp.json();
                if (data.success) {
                    await this.loadUsers();
                }
            } catch (e) {
                console.error('Toggle user error:', e);
            }
        },'''

new_toggle_fn = '''        confirmToggle(user) {
            this.toggleTarget = user;
            this.showToggleModal = true;
        },

        async doToggle() {
            if (!this.toggleTarget) return;
            try {
                const resp = await fetch(`/api/auth/users/${this.toggleTarget.id}/toggle`, { method: 'POST' });
                const data = await resp.json();
                if (data.success) {
                    this.showToggleModal = false;
                    this.toggleTarget = null;
                    await this.loadUsers();
                }
            } catch (e) {
                console.error('Toggle user error:', e);
            }
        },'''

s = s.replace(old_toggle_fn, new_toggle_fn)

p.write_text(s)
print('OK')
