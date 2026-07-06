/**
 * AIDP Web UI - Tool Card Component
 * Reusable tool card with status display
 */

(function(global) {
    'use strict';

    /**
     * Tool Card Component
     * Alpine.js data function for tool cards
     */
    global.AIDP = global.AIDP || {};
    
    global.AIDP.components = global.AIDP.components || {};
    
    global.AIDP.components.ToolCard = function(options = {}) {
        return {
            tool: options.tool || {},
            size: options.size || 'md', // sm, md, lg
            showActions: options.showActions !== false,
            selectable: options.selectable || false,
            selected: false,

            /**
             * Get icon based on tool name
             */
            getToolIcon() {
                const iconMap = {
                    'skill-router': 'fa-route',
                    'knowledge-tool': 'fa-book',
                    'asset-tool': 'fa-box-archive',
                    'sandbox-tool': 'fa-flask',
                    'quality-tool': 'fa-shield-check',
                    'memory-tool': 'fa-brain',
                    'code-index': 'fa-code',
                    'doc-index': 'fa-file-lines',
                    'context-optimizer': 'fa-compress',
                    'evolution-engine': 'fa-dna',
                    'project-importer': 'fa-upload',
                    'controller': 'fa-gamepad'
                };
                return iconMap[this.tool.name] || 'fa-cube';
            },

            /**
             * Get status color class
             */
            getStatusColor() {
                const colors = {
                    'healthy': 'green',
                    'registered': 'yellow',
                    'unhealthy': 'red',
                    'unreachable': 'gray',
                    'disabled': 'gray'
                };
                return colors[this.tool.status] || 'gray';
            },

            /**
             * Get status text
             */
            getStatusText() {
                const texts = {
                    'healthy': '健康',
                    'registered': '已注册',
                    'unhealthy': '异常',
                    'unreachable': '不可达',
                    'disabled': '已禁用'
                };
                return texts[this.tool.status] || this.tool.status;
            },

            /**
             * Get card size classes
             */
            getSizeClasses() {
                const sizes = {
                    'sm': 'p-3',
                    'md': 'p-4',
                    'lg': 'p-5'
                };
                return sizes[this.size] || sizes.md;
            },

            /**
             * Get icon size classes
             */
            getIconSizeClasses() {
                const sizes = {
                    'sm': 'w-8 h-8 text-sm',
                    'md': 'w-10 h-10 text-base',
                    'lg': 'w-12 h-12 text-lg'
                };
                return sizes[this.size] || sizes.md;
            },

            /**
             * Handle card click
             */
            onClick() {
                if (this.selectable) {
                    this.selected = !this.selected;
                    this.$dispatch('tool-selected', { tool: this.tool, selected: this.selected });
                } else {
                    window.location.href = `/tools/${this.tool.name}`;
                }
            },

            /**
             * Handle action click
             */
            onAction(action, event) {
                event.stopPropagation();
                this.$dispatch(`tool-${action}`, { tool: this.tool });
            }
        };
    };

    /**
     * Template for Tool Card (for use with x-html)
     */
    global.AIDP.components.ToolCardTemplate = `
        <div class="tool-card bg-gray-800 rounded-xl border border-gray-700 cursor-pointer transition-all duration-200 hover:border-indigo-500 hover:shadow-lg"
             :class="{ 
                 'border-indigo-500 ring-2 ring-indigo-500/20': selected,
                 [getSizeClasses()]: true
             }"
             @click="onClick()">
            
            <!-- Header: Icon + Status -->
            <div class="flex items-start justify-between mb-3">
                <div class="flex items-center gap-3">
                    <div class="rounded-lg flex items-center justify-center"
                         :class="[getIconSizeClasses(), 'bg-' + getStatusColor() + '-500/20']">
                        <i class="fas" :class="[getToolIcon(), 'text-' + getStatusColor() + '-400']"></i>
                    </div>
                    <div>
                        <h3 class="font-semibold text-white truncate" 
                            :class="size === 'sm' ? 'text-sm' : 'text-base'"
                            x-text="tool.displayName || tool.name"></h3>
                        <p class="text-xs text-gray-500" x-text="tool.name"></p>
                    </div>
                </div>
                <span class="px-2 py-1 rounded-full text-xs font-medium"
                      :class="'bg-' + getStatusColor() + '-500/20 text-' + getStatusColor() + '-400'"
                      x-text="getStatusText()"></span>
            </div>

            <!-- Description -->
            <p x-show="tool.description" 
               class="text-sm text-gray-400 mb-3 line-clamp-2"
               x-text="tool.description"></p>

            <!-- Footer: Stats + Actions -->
            <div class="flex items-center justify-between pt-3 border-t border-gray-700">
                <div class="flex items-center gap-3 text-xs text-gray-500">
                    <span><i class="fas fa-plug mr-1"></i><span x-text="(tool.capabilities || []).length"></span> 能力</span>
                    <span x-show="tool.version"><i class="fas fa-tag mr-1"></i><span x-text="tool.version"></span></span>
                </div>
                
                <!-- Action Buttons -->
                <div x-show="showActions" class="flex items-center gap-1">
                    <button @click="onAction('open', $event)"
                            class="p-1.5 text-gray-400 hover:text-indigo-400 hover:bg-indigo-500/10 rounded transition"
                            title="打开">
                        <i class="fas fa-external-link-alt text-xs"></i>
                    </button>
                    <button @click="onAction('health', $event)"
                            class="p-1.5 text-gray-400 hover:text-green-400 hover:bg-green-500/10 rounded transition"
                            title="健康检查">
                        <i class="fas fa-heartbeat text-xs"></i>
                    </button>
                    <button @click="onAction('settings', $event)"
                            class="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded transition"
                            title="设置">
                        <i class="fas fa-cog text-xs"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

})(window);
