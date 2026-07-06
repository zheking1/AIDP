/**
 * AIDP Web UI - Components Index
 * Register all components
 */

(function(global) {
    'use strict';

    const { components } = global.AIDP;

    /**
     * Register all Alpine.js components
     */
    function registerComponents() {
        // Register component data functions with Alpine
        if (global.Alpine) {
            // Tool Card
            Alpine.data('toolCard', (options) => components.ToolCard(options));
            
            // Status Badge
            Alpine.data('statusBadge', (options) => components.StatusBadge(options));
            Alpine.data('statusDot', (options) => components.StatusDot(options));
            
            // Data Table
            Alpine.data('dataTable', (options) => components.DataTable(options));
        }
    }

    // Auto-register when Alpine is ready
    if (global.Alpine) {
        registerComponents();
    } else {
        document.addEventListener('alpine:init', registerComponents);
    }

    // Export registration function for manual use
    global.AIDP.registerComponents = registerComponents;

})(window);
