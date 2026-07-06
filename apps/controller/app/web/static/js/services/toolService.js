/**
 * AIDP Web UI - Tool Service
 * Business logic for tool management
 */

(function(global) {
    'use strict';

    const { API, store, events, Events } = global.AIDP;

    class ToolService {
        constructor() {
            this.cache = new Map();
            this.cacheTTL = 30000; // 30 seconds
        }

        /**
         * Get all tools
         * @param {Object} options - Query options
         * @param {boolean} options.forceRefresh - Force refresh from server
         * @returns {Promise<Array>} Tools list
         */
        async getTools(options = {}) {
            const { forceRefresh = false } = options;
            
            // Check cache
            if (!forceRefresh && this.cache.has('tools')) {
                const cached = this.cache.get('tools');
                if (Date.now() - cached.timestamp < this.cacheTTL) {
                    return cached.data;
                }
            }

            store.set('tools.loading', true);
            store.set('tools.error', null);

            try {
                const tools = await API.get('/api/tools');
                
                // Update cache
                this.cache.set('tools', {
                    data: tools,
                    timestamp: Date.now()
                });

                // Update store
                store.set('tools.list', tools);
                
                // Emit event
                events.emit(Events.TOOLS_LOADED, tools);

                return tools;
            } catch (error) {
                store.set('tools.error', error.message);
                events.error('Failed to load tools', error);
                throw error;
            } finally {
                store.set('tools.loading', false);
            }
        }

        /**
         * Get single tool by name
         * @param {string} name - Tool name
         * @returns {Promise<Object>} Tool data
         */
        async getTool(name) {
            try {
                return await API.get(`/api/tools/${name}`);
            } catch (error) {
                events.error(`Failed to load tool: ${name}`, error);
                throw error;
            }
        }

        /**
         * Register a new tool
         * @param {Object} toolData - Tool registration data
         * @returns {Promise<Object>} Registered tool
         */
        async registerTool(toolData) {
            try {
                const result = await API.post('/api/tools', toolData);
                
                // Invalidate cache
                this.cache.delete('tools');
                
                // Refresh tools list
                await this.getTools({ forceRefresh: true });
                
                events.notify('Tool registered successfully', 'success');
                
                return result;
            } catch (error) {
                events.error('Failed to register tool', error);
                throw error;
            }
        }

        /**
         * Update tool
         * @param {string} name - Tool name
         * @param {Object} updates - Fields to update
         * @returns {Promise<Object>} Updated tool
         */
        async updateTool(name, updates) {
            try {
                const result = await API.put(`/api/tools/${name}`, updates);
                
                this.cache.delete('tools');
                await this.getTools({ forceRefresh: true });
                
                events.notify('Tool updated successfully', 'success');
                
                return result;
            } catch (error) {
                events.error('Failed to update tool', error);
                throw error;
            }
        }

        /**
         * Delete tool
         * @param {string} name - Tool name
         * @returns {Promise<void>}
         */
        async deleteTool(name) {
            try {
                await API.delete(`/api/tools/${name}`);
                
                this.cache.delete('tools');
                await this.getTools({ forceRefresh: true });
                
                events.notify('Tool deleted successfully', 'success');
            } catch (error) {
                events.error('Failed to delete tool', error);
                throw error;
            }
        }

        /**
         * Check tool health
         * @param {string} name - Tool name
         * @returns {Promise<Object>} Health status
         */
        async checkHealth(name) {
            try {
                const result = await API.post(`/api/tools/${name}/health`);
                
                // Update tool status in store
                const tools = store.get('tools.list');
                const updatedTools = tools.map(t => 
                    t.name === name ? { ...t, status: result.status } : t
                );
                store.set('tools.list', updatedTools);
                
                events.emit(Events.TOOL_STATUS_CHANGED, { name, status: result.status });
                
                return result;
            } catch (error) {
                events.error(`Health check failed for ${name}`, error);
                throw error;
            }
        }

        /**
         * Check health for all tools
         * @returns {Promise<Array>} Health statuses
         */
        async checkAllHealth() {
            try {
                const results = await API.get('/api/tools/health/all');
                
                // Update all tool statuses
                const tools = store.get('tools.list');
                const statusMap = new Map(results.map(r => [r.tool, r.status]));
                
                const updatedTools = tools.map(t => ({
                    ...t,
                    status: statusMap.get(t.name) || t.status
                }));
                
                store.set('tools.list', updatedTools);
                
                return results;
            } catch (error) {
                events.error('Failed to check health for all tools', error);
                throw error;
            }
        }

        /**
         * Sync tool capabilities
         * @param {string} name - Tool name
         * @returns {Promise<Object>} Sync result
         */
        async syncCapabilities(name) {
            try {
                const result = await API.post(`/api/tools/${name}/sync`);
                
                // Refresh tool data
                this.cache.delete('tools');
                await this.getTools({ forceRefresh: true });
                
                events.notify(`Capabilities synced for ${name}`, 'success');
                
                return result;
            } catch (error) {
                events.error(`Failed to sync capabilities for ${name}`, error);
                throw error;
            }
        }

        /**
         * Enable tool
         * @param {string} name - Tool name
         * @returns {Promise<Object>}
         */
        async enableTool(name) {
            try {
                const result = await API.post(`/api/tools/${name}/enable`);
                await this.getTools({ forceRefresh: true });
                events.notify(`Tool ${name} enabled`, 'success');
                return result;
            } catch (error) {
                events.error(`Failed to enable tool ${name}`, error);
                throw error;
            }
        }

        /**
         * Disable tool
         * @param {string} name - Tool name
         * @returns {Promise<Object>}
         */
        async disableTool(name) {
            try {
                const result = await API.post(`/api/tools/${name}/disable`);
                await this.getTools({ forceRefresh: true });
                events.notify(`Tool ${name} disabled`, 'warning');
                return result;
            } catch (error) {
                events.error(`Failed to disable tool ${name}`, error);
                throw error;
            }
        }

        /**
         * Get invocation history
         * @param {Object} options - Query options
         * @returns {Promise<Array>} Invocation history
         */
        async getInvocationHistory(options = {}) {
            const { toolName, limit = 20 } = options;
            
            let url = `/api/tools/invocations/history?limit=${limit}`;
            if (toolName) {
                url += `&tool_name=${encodeURIComponent(toolName)}`;
            }
            
            try {
                return await API.get(url);
            } catch (error) {
                events.error('Failed to load invocation history', error);
                throw error;
            }
        }

        /**
         * Invoke a tool capability
         * @param {string} toolName - Tool name
         * @param {string} capability - Capability name
         * @param {Object} args - Arguments
         * @returns {Promise<Object>} Invocation result
         */
        async invoke(toolName, capability, args = {}) {
            try {
                return await API.post(`/api/tools/${toolName}/invoke`, {
                    capability,
                    arguments: args
                });
            } catch (error) {
                events.error(`Failed to invoke ${toolName}.${capability}`, error);
                throw error;
            }
        }

        /**
         * Filter tools based on criteria
         * @param {Object} criteria - Filter criteria
         * @returns {Array} Filtered tools
         */
        filterTools(criteria = {}) {
            const tools = store.get('tools.list') || [];
            const { query = '', status = '' } = criteria;
            
            return tools.filter(tool => {
                // Text search
                if (query) {
                    const q = query.toLowerCase();
                    const matchesName = tool.name?.toLowerCase().includes(q);
                    const matchesDisplay = tool.displayName?.toLowerCase().includes(q);
                    if (!matchesName && !matchesDisplay) return false;
                }
                
                // Status filter
                if (status && tool.status !== status) {
                    return false;
                }
                
                return true;
            });
        }

        /**
         * Sort tools
         * @param {Array} tools - Tools to sort
         * @param {string} sortBy - Sort field
         * @param {string} order - Sort order (asc|desc)
         * @returns {Array} Sorted tools
         */
        sortTools(tools, sortBy = 'name', order = 'asc') {
            const sorted = [...tools].sort((a, b) => {
                let aVal, bVal;
                
                switch (sortBy) {
                    case 'name':
                        aVal = a.displayName || a.name;
                        bVal = b.displayName || b.name;
                        break;
                    case 'status':
                        aVal = a.status;
                        bVal = b.status;
                        break;
                    case 'updated':
                        aVal = new Date(a.updatedAt || 0);
                        bVal = new Date(b.updatedAt || 0);
                        break;
                    default:
                        return 0;
                }
                
                if (aVal < bVal) return order === 'asc' ? -1 : 1;
                if (aVal > bVal) return order === 'asc' ? 1 : -1;
                return 0;
            });
            
            return sorted;
        }

        /**
         * Get tool statistics
         * @returns {Object} Statistics
         */
        getStats() {
            const tools = store.get('tools.list') || [];
            
            return {
                total: tools.length,
                healthy: tools.filter(t => t.status === 'healthy').length,
                registered: tools.filter(t => t.status === 'registered').length,
                unhealthy: tools.filter(t => t.status === 'unhealthy' || t.status === 'unreachable').length,
                disabled: tools.filter(t => t.status === 'disabled').length
            };
        }

        /**
         * Clear cache
         */
        clearCache() {
            this.cache.clear();
        }
    }

    // Create singleton instance
    const toolService = new ToolService();

    // Auto-refresh health every 60 seconds
    setInterval(() => {
        if (document.visibilityState === 'visible') {
            toolService.checkAllHealth().catch(() => {});
        }
    }, 60000);

    // Export
    global.AIDP = global.AIDP || {};
    global.AIDP.ToolService = ToolService;
    global.AIDP.toolService = toolService;

})(window);
