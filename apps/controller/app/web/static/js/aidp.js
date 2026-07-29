/**
 * AIDP Web UI - Main Entry Point
 * Loads all modules and initializes the application
 */

(function(global) {
    'use strict';

    // AIDP Namespace
    global.AIDP = global.AIDP || {};

    const AIDP = global.AIDP;

    /**
     * Application configuration
     */
    AIDP.config = {
        version: '1.0.0',
        apiBaseUrl: '',
        refreshInterval: 60000,
        enableLogging: true
    };

    /**
     * Logger utility
     */
    AIDP.log = {
        debug: (...args) => AIDP.config.enableLogging && console.debug('[AIDP]', ...args),
        info: (...args) => AIDP.config.enableLogging && console.info('[AIDP]', ...args),
        warn: (...args) => console.warn('[AIDP]', ...args),
        error: (...args) => console.error('[AIDP]', ...args)
    };

    /**
     * Initialize AIDP application
     */
    AIDP.init = function(options = {}) {
        // Merge config
        Object.assign(AIDP.config, options);

        AIDP.log.info('Initializing AIDP Web UI v' + AIDP.config.version);

        // Initialize store with user data
        if (options.user) {
            AIDP.store.set('user', options.user);
        }

        // Load initial data
        AIDP.loadInitialData();

        // Setup event listeners
        AIDP.setupEventListeners();

        AIDP.log.info('AIDP Web UI initialized');
    };

    /**
     * Load initial application data
     */
    AIDP.loadInitialData = async function() {
        try {
            // Load tools
            await AIDP.toolService.getTools();
            AIDP.log.info('Tools loaded:', AIDP.store.get('tools.list').length);
        } catch (error) {
            AIDP.log.error('Failed to load initial data:', error);
        }
    };

    /**
     * Setup global event listeners
     */
    AIDP.setupEventListeners = function() {
        // Handle navigation
        AIDP.events.on(AIDP.Events.NAVIGATE, (data) => {
            if (data.url) {
                window.location.href = data.url;
            }
        });

        // Handle errors
        AIDP.events.on(AIDP.Events.ERROR_OCCURRED, (data) => {
            AIDP.log.error('Application error:', data.error);
        });

        // Visibility change - refresh data when tab becomes visible
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                AIDP.toolService.getTools().catch(() => {});
            }
        });
    };

    /**
     * Global Alpine.js data for layouts
     */
    AIDP.layoutData = function() {
        return {
            sidebarCollapsed: false,
            currentPage: 'dashboard',
            notifications: [],
            
            init() {
                // Load saved preferences
                const saved = localStorage.getItem('aidp:preferences');
                if (saved) {
                    try {
                        const prefs = JSON.parse(saved);
                        this.sidebarCollapsed = prefs.sidebarCollapsed || false;
                    } catch (e) {}
                }

                // Listen for page changes
                AIDP.events.on(AIDP.Events.PAGE_CHANGED, (data) => {
                    this.currentPage = data.page;
                });

                // Listen for notifications
                AIDP.events.on(AIDP.Events.NOTIFICATION_SHOW, (data) => {
                    this.showNotification(data);
                });
            },

            toggleSidebar() {
                this.sidebarCollapsed = !this.sidebarCollapsed;
                this.savePreferences();
            },

            savePreferences() {
                const prefs = {
                    sidebarCollapsed: this.sidebarCollapsed
                };
                localStorage.setItem('aidp:preferences', JSON.stringify(prefs));
            },

            showNotification(data) {
                const id = Date.now();
                const notification = {
                    id,
                    message: data.message,
                    type: data.type || 'info',
                    duration: data.duration || 3000
                };

                this.notifications.push(notification);

                // Auto remove
                setTimeout(() => {
                    this.removeNotification(id);
                }, notification.duration);
            },

            removeNotification(id) {
                const index = this.notifications.findIndex(n => n.id === id);
                if (index > -1) {
                    this.notifications.splice(index, 1);
                }
            },

            getNotificationClass(type) {
                const classes = {
                    'info': 'bg-blue-500',
                    'success': 'bg-green-500',
                    'warning': 'bg-yellow-500',
                    'error': 'bg-red-500'
                };
                return classes[type] || classes.info;
            }
        };
    };

    /**
     * Dashboard page data
     */
    AIDP.dashboardData = function() {
        return {
            tools: [],
            invocations: [],
            projectCount: 0,
            loading: true,

            async init() {
                AIDP.events.emit(AIDP.Events.PAGE_CHANGED, { page: 'dashboard' });
                
                // Subscribe to tools updates
                AIDP.store.subscribe('tools.list', (tools) => {
                    this.tools = tools;
                });

                // Load all data
                await Promise.all([
                    this.loadTools(),
                    this.loadInvocations(),
                    this.loadProjectCount()
                ]);

                this.loading = false;

                // Auto refresh
                setInterval(() => this.refreshData(), AIDP.config.refreshInterval);
            },

            async loadTools() {
                try {
                    this.tools = await AIDP.toolService.getTools();
                } catch (e) {
                    this.tools = [];
                }
            },

            async loadInvocations() {
                try {
                    this.invocations = await AIDP.toolService.getInvocationHistory({ limit: 10 });
                } catch (e) {
                    this.invocations = [];
                }
            },

            async loadProjectCount() {
                try {
                    const projects = await AIDP.API.get('/api/projects');
                    this.projectCount = projects.length || 0;
                } catch (e) {
                    this.projectCount = 0;
                }
            },

            async refreshData() {
                await AIDP.toolService.getTools({ forceRefresh: true });
                await this.loadInvocations();
            },

            get healthyCount() {
                return this.tools.filter(t => t.status === 'healthy').length;
            },

            getStatusColor(status) {
                const colors = {
                    'healthy': 'green',
                    'registered': 'yellow',
                    'unhealthy': 'red',
                    'unreachable': 'gray',
                    'disabled': 'gray'
                };
                return colors[status] || 'gray';
            },

            formatTime(iso) {
                if (!iso) return '-';
                const d = new Date(iso);
                return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
            }
        };
    };

    /**
     * Tools page data
     */
    AIDP.toolsPageData = function() {
        return {
            tools: [],
            loading: false,
            searchQuery: '',
            statusFilter: '',
            sortBy: 'name',
            refreshing: false,

            async init() {
                AIDP.events.emit(AIDP.Events.PAGE_CHANGED, { page: 'tools' });

                // Subscribe to tools updates
                AIDP.store.subscribe('tools.list', (tools) => {
                    this.tools = tools;
                });

                await this.loadTools();
            },

            async loadTools() {
                this.loading = true;
                try {
                    await AIDP.toolService.getTools();
                } finally {
                    this.loading = false;
                }
            },

            get filteredTools() {
                let result = [...this.tools];

                if (this.searchQuery) {
                    const q = this.searchQuery.toLowerCase();
                    result = result.filter(t => 
                        (t.name && t.name.toLowerCase().includes(q)) ||
                        (t.displayName && t.displayName.toLowerCase().includes(q))
                    );
                }

                if (this.statusFilter) {
                    result = result.filter(t => t.status === this.statusFilter);
                }

                // Sort
                result.sort((a, b) => {
                    const aVal = (a.displayName || a.name).toLowerCase();
                    const bVal = (b.displayName || b.name).toLowerCase();
                    return aVal.localeCompare(bVal);
                });

                return result;
            },

            async refreshAllHealth() {
                this.refreshing = true;
                try {
                    await AIDP.toolService.checkAllHealth();
                } finally {
                    this.refreshing = false;
                }
            },

            async checkHealth(name) {
                await AIDP.toolService.checkHealth(name);
            },

            async syncCapabilities(name) {
                await AIDP.toolService.syncCapabilities(name);
            },

            async toggleTool(tool) {
                if (tool.status === 'disabled') {
                    await AIDP.toolService.enableTool(tool.name);
                } else {
                    await AIDP.toolService.disableTool(tool.name);
                }
            },

            formatTime(iso) {
                if (!iso) return '-';
                const d = new Date(iso);
                return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
            }
        };
    };

    /**
     * Tool detail page data
     */
    AIDP.toolDetailData = function(toolName) {
        return {
            toolName,
            tool: null,
            loading: true,
            error: null,
            activeTab: 'overview',
            webuiLoading: false,

            async init() {
                AIDP.events.emit(AIDP.Events.PAGE_CHANGED, { page: 'tool-detail', tool: toolName });
                await this.loadTool();
            },

            async loadTool() {
                this.loading = true;
                this.error = null;
                try {
                    this.tool = await AIDP.toolService.getTool(this.toolName);
                    AIDP.store.set('tools.selected', this.tool);
                } catch (e) {
                    this.error = e.message;
                } finally {
                    this.loading = false;
                }
            },

            async switchToWebUI() {
                this.activeTab = 'webui';
                this.webuiLoading = true;
                const el = document.getElementById('tool-webui-content');
                if (!el) return;
                if (el.children.length > 0) { this.webuiLoading = false; return; }
                try {
                    const resp = await fetch('/tools/' + this.toolName + '/web/?partial=1');
                    if (!resp.ok) throw new Error('HTTP ' + resp.status);
                    let html = await resp.text();
                    const scripts = [];
                    html = html.replace(/<script>([\s\S]*?)<\/script>/g, function(m, c) { scripts.push(c); return ''; });
                    el.innerHTML = html;
                    scripts.forEach(function(code) {
                        try {
                            var t = code.trim();
                            if (t.startsWith('function ')) { var m = t.match(/^function\s+(\w+)/); if (m) eval('window.' + m[1] + ' = ' + t); else eval(code); }
                            else eval(code);
                        } catch(e) { console.warn(e.message); }
                    });
                    if (window.Alpine) Alpine.initTree(el);
                } catch(e) { console.error('WebUI load failed:', e); }
                finally { this.webuiLoading = false; }
            },

            async checkHealth() {
                if (!this.tool) return;
                await AIDP.toolService.checkHealth(this.toolName);
                await this.loadTool();
            },

            async syncCapabilities() {
                if (!this.tool) return;
                await AIDP.toolService.syncCapabilities(this.toolName);
                await this.loadTool();
            },

            get capabilities() {
                return this.tool?.capabilities || [];
            },

            getStatusColor(status) {
                var colors = { 'healthy': 'green', 'registered': 'yellow', 'unhealthy': 'red', 'unreachable': 'gray', 'disabled': 'gray' };
                return colors[status] || 'gray';
            }
        };
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => AIDP.init());
    } else {
        // DOM already loaded
        setTimeout(() => AIDP.init(), 0);
    }

})(window);
