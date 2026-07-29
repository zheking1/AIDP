// Memory Tool UI Utilities

/**
 * Toast notification system
 */
const Toast = {
    container: null,
    
    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'fixed bottom-4 right-4 z-50 space-y-2';
            document.body.appendChild(this.container);
        }
    },
    
    show(message, type = 'info', duration = 3000) {
        this.init();
        
        const colors = {
            info: 'bg-blue-600',
            success: 'bg-green-600',
            warning: 'bg-yellow-600',
            error: 'bg-red-600',
        };
        
        const icons = {
            info: 'ℹ️',
            success: '✓',
            warning: '⚠️',
            error: '✗',
        };
        
        const toast = document.createElement('div');
        toast.className = `${colors[type]} text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 min-w-[200px] transform transition-all duration-300 translate-x-full opacity-0`;
        toast.innerHTML = `
            <span class="text-lg">${icons[type]}</span>
            <span class="flex-1">${message}</span>
            <button class="text-white/70 hover:text-white" onclick="this.parentElement.remove()">×</button>
        `;
        
        this.container.appendChild(toast);
        
        // Animate in
        requestAnimationFrame(() => {
            toast.classList.remove('translate-x-full', 'opacity-0');
        });
        
        // Auto remove
        setTimeout(() => {
            toast.classList.add('translate-x-full', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },
    
    success(message, duration) {
        this.show(message, 'success', duration);
    },
    
    error(message, duration) {
        this.show(message, 'error', duration);
    },
    
    info(message, duration) {
        this.show(message, 'info', duration);
    },
    
    warning(message, duration) {
        this.show(message, 'warning', duration);
    },
};

/**
 * Confirmation dialog
 */
const Confirm = {
    async dialog(message, title = '确认') {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4';
            modal.innerHTML = `
                <div class="bg-white rounded-lg shadow-xl max-w-sm w-full p-6 transform scale-95 transition-transform duration-200">
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">${title}</h3>
                    <p class="text-gray-600 mb-6">${message}</p>
                    <div class="flex justify-end gap-3">
                        <button class="cancel px-4 py-2 text-gray-600 hover:text-gray-800">取消</button>
                        <button class="confirm px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">确认</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Animate in
            requestAnimationFrame(() => {
                modal.querySelector('.bg-white').classList.remove('scale-95');
            });
            
            // Handle buttons
            modal.querySelector('.cancel').onclick = () => {
                modal.remove();
                resolve(false);
            };
            
            modal.querySelector('.confirm').onclick = () => {
                modal.remove();
                resolve(true);
            };
            
            // Click outside to close
            modal.onclick = (e) => {
                if (e.target === modal) {
                    modal.remove();
                    resolve(false);
                }
            };
        });
    },
    
    async delete(itemName = '此项') {
        return this.dialog(`确定要删除${itemName}吗？此操作不可恢复。`, '删除确认');
    },
};

/**
 * API request helper with error handling
 */
const API = {
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        try {
            const resp = await fetch(url, { ...defaultOptions, ...options });
            
            if (!resp.ok) {
                const error = await resp.json().catch(() => ({ detail: '请求失败' }));
                throw new Error(error.detail || `HTTP ${resp.status}`);
            }
            
            const data = await resp.json();
            return { success: true, data };
        } catch (error) {
            console.error('API Error:', error);
            Toast.error(error.message || '请求失败');
            return { success: false, error: error.message };
        }
    },
    
    get(url) {
        return this.request(url, { method: 'GET' });
    },
    
    post(url, data) {
        return this.request(url, { 
            method: 'POST', 
            body: JSON.stringify(data) 
        });
    },
    
    put(url, data) {
        return this.request(url, { 
            method: 'PUT', 
            body: JSON.stringify(data) 
        });
    },
    
    delete(url) {
        return this.request(url, { method: 'DELETE' });
    },
};

/**
 * Format utilities
 */
const Format = {
    date(dateStr, withTime = false) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const options = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
        };
        if (withTime) {
            options.hour = '2-digit';
            options.minute = '2-digit';
        }
        return date.toLocaleString('zh-CN', options);
    },
    
    number(num, decimals = 0) {
        if (num === null || num === undefined) return '-';
        return Number(num).toFixed(decimals);
    },
    
    fileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
};

/**
 * Category utilities
 */
const Category = {
    labels: {
        architecture: '架构',
        decision: '决策',
        pattern: '模式',
        issue: '问题',
        bug: '缺陷',
        other: '其他',
    },
    
    classes: {
        architecture: 'bg-blue-100 text-blue-700',
        decision: 'bg-green-100 text-green-700',
        pattern: 'bg-amber-100 text-amber-700',
        issue: 'bg-orange-100 text-orange-700',
        bug: 'bg-red-100 text-red-700',
        other: 'bg-gray-100 text-gray-700',
    },
    
    icons: {
        architecture: '🏗️',
        decision: '🤔',
        pattern: '📐',
        issue: '⚠️',
        bug: '🐛',
        other: '📦',
    },
    
    getLabel(category) {
        return this.labels[category] || category;
    },
    
    getClass(category) {
        return this.classes[category] || 'bg-gray-100 text-gray-700';
    },
    
    getIcon(category) {
        return this.icons[category] || '📄';
    },
};

// Export for use in Alpine.js
window.MemoryUtils = { Toast, Confirm, API, Format, Category };
