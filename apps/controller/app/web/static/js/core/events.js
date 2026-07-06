/**
 * AIDP Web UI - Event Bus Module
 * Decoupled event communication between components
 */

(function(global) {
    'use strict';

    class EventBus {
        constructor() {
            this.events = new Map();
            this.onceEvents = new Map();
            this.maxListeners = 100;
        }

        /**
         * Subscribe to an event
         * @param {string} event - Event name
         * @param {Function} callback - Event handler
         * @returns {Function} Unsubscribe function
         */
        on(event, callback) {
            if (!this.events.has(event)) {
                this.events.set(event, new Set());
            }
            
            const listeners = this.events.get(event);
            
            if (listeners.size >= this.maxListeners) {
                console.warn(`Max listeners (${this.maxListeners}) reached for event: ${event}`);
            }
            
            listeners.add(callback);
            
            // Return unsubscribe function
            return () => this.off(event, callback);
        }

        /**
         * Subscribe to an event once
         * @param {string} event - Event name
         * @param {Function} callback - Event handler
         * @returns {Function} Unsubscribe function
         */
        once(event, callback) {
            const onceWrapper = (data) => {
                this.off(event, onceWrapper);
                callback(data);
            };
            
            return this.on(event, onceWrapper);
        }

        /**
         * Unsubscribe from an event
         * @param {string} event - Event name
         * @param {Function} callback - Event handler to remove
         */
        off(event, callback) {
            if (!this.events.has(event)) return;
            
            const listeners = this.events.get(event);
            listeners.delete(callback);
            
            if (listeners.size === 0) {
                this.events.delete(event);
            }
        }

        /**
         * Emit an event
         * @param {string} event - Event name
         * @param {*} data - Event data
         */
        emit(event, data) {
            if (!this.events.has(event)) return;
            
            const listeners = this.events.get(event);
            listeners.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }

        /**
         * Emit event asynchronously
         * @param {string} event - Event name
         * @param {*} data - Event data
         */
        async emitAsync(event, data) {
            if (!this.events.has(event)) return;
            
            const listeners = Array.from(this.events.get(event));
            await Promise.all(listeners.map(async callback => {
                try {
                    await callback(data);
                } catch (error) {
                    console.error(`Error in async event handler for ${event}:`, error);
                }
            }));
        }

        /**
         * Remove all listeners for an event
         * @param {string} event - Event name (optional, removes all if not specified)
         */
        removeAll(event) {
            if (event) {
                this.events.delete(event);
            } else {
                this.events.clear();
            }
        }

        /**
         * Get listener count for an event
         * @param {string} event - Event name
         * @returns {number} Number of listeners
         */
        listenerCount(event) {
            return this.events.get(event)?.size || 0;
        }

        /**
         * Get all event names
         * @returns {Array} Array of event names
         */
        eventNames() {
            return Array.from(this.events.keys());
        }
    }

    // Predefined events
    const Events = {
        // Tool events
        TOOLS_LOADED: 'tools:loaded',
        TOOL_SELECTED: 'tool:selected',
        TOOL_STATUS_CHANGED: 'tool:status_changed',
        TOOL_HEALTH_CHECK: 'tool:health_check',
        
        // Dashboard events
        DASHBOARD_REFRESH: 'dashboard:refresh',
        STATS_UPDATED: 'stats:updated',
        
        // UI events
        PAGE_CHANGED: 'page:changed',
        MODAL_OPEN: 'modal:open',
        MODAL_CLOSE: 'modal:close',
        NOTIFICATION_SHOW: 'notification:show',
        NOTIFICATION_HIDE: 'notification:hide',
        SIDEBAR_TOGGLE: 'sidebar:toggle',
        
        // Navigation events
        NAVIGATE: 'navigate',
        
        // Error events
        ERROR_OCCURRED: 'error:occurred',
        ERROR_CLEARED: 'error:cleared',
        
        // Loading events
        LOADING_START: 'loading:start',
        LOADING_END: 'loading:end'
    };

    // Create global event bus instance
    const eventBus = new EventBus();

    // Helper for notifications
    eventBus.notify = function(message, type = 'info', duration = 3000) {
        this.emit(Events.NOTIFICATION_SHOW, { message, type, duration });
    };

    // Helper for errors
    eventBus.error = function(message, error = null) {
        console.error(message, error);
        this.emit(Events.ERROR_OCCURRED, { message, error });
        this.notify(message, 'error', 5000);
    };

    // Helper for loading states
    eventBus.loading = function(promise, message = 'Loading...') {
        this.emit(Events.LOADING_START, { message });
        
        promise
            .finally(() => {
                this.emit(Events.LOADING_END);
            });
        
        return promise;
    };

    // Export
    global.AIDP = global.AIDP || {};
    global.AIDP.EventBus = EventBus;
    global.AIDP.events = eventBus;
    global.AIDP.Events = Events;

})(window);
