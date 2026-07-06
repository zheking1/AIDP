from pathlib import Path
p = Path('/home/docker/AI-Code/controller/app/web/templates/admin/user_detail.html')
s = p.read_text()

# Add reset password state
old = '''        actionLabels: {
            'login': '登录',
            'logout': '登出',
            'login_failed': '登录失败'
        },'''

new = '''        showResetModal: false,
        newPassword: '',
        resetError: '',
        resetting: false,
        actionLabels: {
            'login': '登录',
            'logout': '登出',
            'login_failed': '登录失败'
        },'''

s = s.replace(old, new)

# Add reset password function before formatDate
old = '''        formatDate(iso) {'''

new = '''        async resetPassword() {
            if (!this.newPassword || this.newPassword.length < 6) {
                this.resetError = '密码至少 6 个字符';
                return;
            }
            this.resetting = true;
            this.resetError = '';
            try {
                const resp = await fetch(`/api/auth/users/${this.userId}/reset-password`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: this.userId, new_password: this.newPassword })
                });
                const data = await resp.json();
                if (data.success) {
                    this.showResetModal = false;
                    this.newPassword = '';
                    alert('密码重置成功');
                } else {
                    this.resetError = data.detail || '重置失败';
                }
            } catch (e) {
                this.resetError = '网络错误';
            } finally {
                this.resetting = false;
            }
        },

        formatDate(iso) {'''

s = s.replace(old, new)

p.write_text(s)
print('OK')
