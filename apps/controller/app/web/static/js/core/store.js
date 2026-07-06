/**
 * AIDP Web UI - State Management Module
 * Simple centralized state store with reactivity
 */

(function(global) {
    'use strict';

    class Store {
        constructor(initialState = {}) {
            this.state = { ...initialState };
            this.listeners = new Map();
            this.computedCache = new Map();
        }

        /**
         * Get state value by path (supports nested: 'tools.list')
         */
        get(path) {
            if (!path) return this.state;
            
            const keys = path.split('.');
            let value = this.state;
            
            for (const key of keys) {
                if (value === null || value === undefined) return undefined;
                value = value[key];
            }
            
            return value;
        }

        /**
         * Set state value by path
         */
        set(path, value) {
            const keys = path.split('.');
            const lastKey = keys.pop();
            let target = this.state;
            
            for (const key of keys) {
                if (!(key in target) || typeof target[key] !== 'object') {
                    target[key] = {};
                }
                target = target[key];
            }
            
            const oldValue = target[lastKey];
            target[lastKey] = value;
            
            // Notify listeners
            this.notify(path, value, oldValue);
            this.notify('*', this.state, null);
            
            return this;
        }

        /**
         * Update state with object merge
         */
        update(updates) {
            const oldState = { ...this.state };
            this.state = this.deepMerge(this.state, updates);
            this.notify('*', this.state, oldState);
            return this;
        }

        /**
         * Subscribe to state changes
         */
        subscribe(path, callback) {
            if (!this.listeners.has(path)) {
                this.listeners.set(path, new Set());
            }
            this.listeners.get(path).add(callback);
            
            // Return unsubscribe function
            return () => {
                this.listeners.get(path)?.delete(callback);
            };
        }

        /**
         * Notify listeners of state change
         */
        notify(path, newValue, oldValue) {
            // Notify exact path listeners
            this.listeners.get(path)?.forEach(cb => cb(newValue, oldValue, path));
            
            // Notify wildcard listeners
            if (path !== '*') {
                this.listeners.get('*')?.forEach(cb => cb(this.state, null, path));
            }
            
            // Notify parent path listeners
            const parts = path.split('.');
            while (parts.length > 1) {
                parts.pop();
                const parentPath = parts.join('.');
                this.listeners.get(parentPath)?.forEach(cb => 
                    cb(this.get(parentPath), null, path)
                );
            }
        }

        /**
         * Deep merge objects
         */
        deepMerge(target, source) {
            if (!source || typeof source !== 'object') return source;
            if (!target || typeof target !== 'object') return { ...source };
            
            const result = { ...target };
            
            for (const key in source) {
                if (source.hasOwnProperty(key)) {
                    if (source[key] instanceof Array) {
                        result[key] = [...source[key]];
                    } else if (typeof source[key] === 'object' && source[key] !== null) {
                        result[key] = this.deepMerge(result[key], source[key]);
                    } else {
                        result[key] = source[key];
                    }
                }
            }
            
            return result;
        }

        /**
         * Define computed property
         */
        computed(name, computeFn) {
            Object.defineProperty(this, name, {
                get: () => {
                    if (!this.computedCache.has(name)) {
                        this.computedCache.set(name, computeFn(this.state));
                        
                        // Recompute on state change
                        this.subscribe('*', () => {
                            this.computedCache.set(name, computeFn(this.state));
                        });
                    }
                    return this.computedCache.get(name);
                }
            });
        }

        /**
         * Batch multiple updates
         */
        batch(updateFn) {
            const originalNotify = this.notify;
            const pendingPaths = new Set();
            
            // Collect notifications
            this.notify = (path) => {
                pendingPaths.add(path);
            };
            
            try {
                updateFn(this);
            } finally {
                // Restore notify and fire collected notifications
                this.notify = originalNotify;
                pendingPaths.forEach(path => {
                    this.notify(path, this.get(path), null);
                });
            }
        }

        /**
         * Reset state to initial
         */
        reset(initialState) {
            this.state = { ...initialState };
            this.listeners.clear();
            this.computedCache.clear();
        }

        /**
         * Create Alpine.js compatible data object
         */
        toAlpineData() {
            return {
                store: this,
                state: this.state,
                
                init() {
                    // Sync Alpine data with store
                    this.store.subscribe('*', (newState) => {
                        this.state = newState;
                    });
                },
                
                get(path) {
                    return this.store.get(path);
                },
                
                set(path, value) {
                    this.store.set(path, value);
                }
            };
        }
    }

    // Create global store instance
    const globalStore = new Store({
        // Tools state
        tools: {
            list: [],
            loading: false,
            error: null,
            selected: null,
            filter: {
                query: '',
                status: ''
            }
        },
        
        // Dashboard state
        dashboard: {
            stats: {
                totalTools: 0,
                healthyTools: 0,
                totalProjects: 0,
                recentInvocations: []
            },
            loading: false
        },
        
        // UI state
        ui: {
            sidebarCollapsed: false,
            currentPage: 'dashboard',
            modal: null,
            notifications: []
        },
        
        // User state
        user: {
            id: null,
            name: '',
            role: 'user'
        }
    });

    // Export
    global.AIDP = global.AIDP || {};
    global.AIDP.Store = Store;
    global.AIDP.store = globalStore;

})(window);
