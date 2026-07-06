/**
 * AIDP Web UI - Status Badge Component
 * Standardized status display component
 */

(function(global) {
    'use strict';

    global.AIDP = global.AIDP || {};
    global.AIDP.components = global.AIDP.components || {};

    /**
     * Status Badge Component
     */
    global.AIDP.components.StatusBadge = function(options = {}) {
        return {
            status: options.status || 'unknown',
            size: options.size || 'md', // sm, md, lg
            showDot: options.showDot !== false,
            showText: options.showText !== false,
            text: options.text || null, // Custom text override

            /**
             * Get status configuration
             */
            getConfig() {
                const configs = {
                    'healthy': {
                        color: 'green',
                        bg: 'bg-green-500/20',
                        text: 'text-green-400',
                        dot: 'bg-green-500',
                        label: '健康'
                    },
                    'registered': {
                        color: 'yellow',
                        bg: 'bg-yellow-500/20',
                        text: 'text-yellow-400',
                        dot: 'bg-yellow-500',
                        label: '已注册'
                    },
                    'unhealthy': {
                        color: 'red',
                        bg: 'bg-red-500/20',
                        text: 'text-red-400',
                        dot: 'bg-red-500',
                        label: '异常'
                    },
                    'unreachable': {
                        color: 'gray',
                        bg: 'bg-gray-500/20',
                        text: 'text-gray-400',
                        dot: 'bg-gray-500',
                        label: '不可达'
                    },
                    'disabled': {
                        color: 'gray',
                        bg: 'bg-gray-600/20',
                        text: 'text-gray-500',
                        dot: 'bg-gray-600',
                        label: '已禁用'
                    },
                    'loading': {
                        color: 'blue',
                        bg: 'bg-blue-500/20',
                        text: 'text-blue-400',
                        dot: 'bg-blue-500 animate-pulse',
                        label: '加载中'
                    },
                    'unknown': {
                        color: 'gray',
                        bg: 'bg-gray-500/20',
                        text: 'text-gray-400',
                        dot: 'bg-gray-500',
                        label: '未知'
                    }
                };
                return configs[this.status] || configs.unknown;
            },

            /**
             * Get size classes
             */
            getSizeClasses() {
                const sizes = {
                    'sm': 'px-1.5 py-0.5 text-xs',
                    'md': 'px-2 py-1 text-sm',
                    'lg': 'px-3 py-1.5 text-base'
                };
                return sizes[this.size] || sizes.md;
            },

            /**
             * Get dot size
             */
            getDotSize() {
                const sizes = {
                    'sm': 'w-1.5 h-1.5',
                    'md': 'w-2 h-2',
                    'lg': 'w-2.5 h-2.5'
                };
                return sizes[this.size] || sizes.md;
            },

            /**
             * Get display text
             */
            getDisplayText() {
                return this.text || this.getConfig().label;
            },

            /**
             * Get all classes
             */
            getClasses() {
                const config = this.getConfig();
                return `inline-flex items-center gap-1.5 rounded-full font-medium ${config.bg} ${config.text} ${this.getSizeClasses()}`;
            }
        };
    };

    /**
     * Status Badge Template
     */
    global.AIDP.components.StatusBadgeTemplate = `
        <span :class="getClasses()">
            <span x-show="showDot" 
                  class="rounded-full"
                  :class="[getDotSize(), getConfig().dot]"></span>
            <span x-show="showText" x-text="getDisplayText()"></span>
        </span>
    `;

    /**
     * Status Dot Component (simpler version)
     */
    global.AIDP.components.StatusDot = function(options = {}) {
        return {
            status: options.status || 'unknown',
            size: options.size || 'md',
            pulse: options.pulse || false,

            getClasses() {
                const config = global.AIDP.components.StatusBadge({ status: this.status }).getConfig();
                const sizes = {
                    'sm': 'w-2 h-2',
                    'md': 'w-2.5 h-2.5',
                    'lg': 'w-3 h-3'
                };
                const sizeClass = sizes[this.size] || sizes.md;
                const pulseClass = this.pulse ? 'animate-pulse' : '';
                
                return `rounded-full ${sizeClass} ${config.dot} ${pulseClass}`;
            }
        };
    };

    global.AIDP.components.StatusDotTemplate = `
        <span :class="getClasses()"></span>
    `;

})(window);
