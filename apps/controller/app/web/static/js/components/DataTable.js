/**
 * AIDP Web UI - Data Table Component
 * Reusable data table with sorting, filtering, pagination
 */

(function(global) {
    'use strict';

    global.AIDP = global.AIDP || {};
    global.AIDP.components = global.AIDP.components || {};

    /**
     * Data Table Component
     */
    global.AIDP.components.DataTable = function(options = {}) {
        return {
            // Data
            data: options.data || [],
            columns: options.columns || [],
            
            // State
            loading: false,
            error: null,
            
            // Sorting
            sortColumn: options.sortColumn || null,
            sortDirection: options.sortDirection || 'asc', // asc, desc
            
            // Pagination
            pagination: options.pagination !== false,
            page: options.page || 1,
            pageSize: options.pageSize || 10,
            total: options.total || 0,
            
            // Selection
            selectable: options.selectable || false,
            selectedIds: new Set(),
            
            // Search
            searchable: options.searchable !== false,
            searchQuery: '',
            
            // Row actions
            rowActions: options.rowActions || [],

            /**
             * Initialize component
             */
            init() {
                if (options.onInit) {
                    options.onInit(this);
                }
            },

            /**
             * Get filtered and sorted data
             */
            get processedData() {
                let result = [...this.data];

                // Filter by search
                if (this.searchQuery && this.searchable) {
                    const q = this.searchQuery.toLowerCase();
                    result = result.filter(row => {
                        return this.columns.some(col => {
                            const value = this.getCellValue(row, col.key);
                            return String(value).toLowerCase().includes(q);
                        });
                    });
                }

                // Sort
                if (this.sortColumn) {
                    result.sort((a, b) => {
                        const aVal = this.getCellValue(a, this.sortColumn);
                        const bVal = this.getCellValue(b, this.sortColumn);
                        
                        let comparison = 0;
                        if (aVal < bVal) comparison = -1;
                        if (aVal > bVal) comparison = 1;
                        
                        return this.sortDirection === 'asc' ? comparison : -comparison;
                    });
                }

                return result;
            },

            /**
             * Get paginated data
             */
            get paginatedData() {
                if (!this.pagination) {
                    return this.processedData;
                }
                
                const start = (this.page - 1) * this.pageSize;
                return this.processedData.slice(start, start + this.pageSize);
            },

            /**
             * Get total pages
             */
            get totalPages() {
                return Math.ceil(this.processedData.length / this.pageSize);
            },

            /**
             * Get cell value from row
             */
            getCellValue(row, key) {
                const keys = key.split('.');
                let value = row;
                for (const k of keys) {
                    value = value?.[k];
                }
                return value;
            },

            /**
             * Format cell value
             */
            formatCell(value, column) {
                if (column.formatter) {
                    return column.formatter(value);
                }
                
                if (value === null || value === undefined) {
                    return '-';
                }
                
                return value;
            },

            /**
             * Handle sort
             */
            onSort(column) {
                if (!column.sortable) return;
                
                if (this.sortColumn === column.key) {
                    this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    this.sortColumn = column.key;
                    this.sortDirection = 'asc';
                }
                
                this.$dispatch('sort', { column: this.sortColumn, direction: this.sortDirection });
            },

            /**
             * Get sort icon
             */
            getSortIcon(column) {
                if (this.sortColumn !== column.key) {
                    return 'fa-sort text-gray-600';
                }
                return this.sortDirection === 'asc' ? 'fa-sort-up text-indigo-400' : 'fa-sort-down text-indigo-400';
            },

            /**
             * Handle page change
             */
            onPageChange(page) {
                if (page < 1 || page > this.totalPages) return;
                this.page = page;
                this.$dispatch('page-change', { page });
            },

            /**
             * Handle row selection
             */
            onSelect(row) {
                if (!this.selectable) return;
                
                const id = row.id || row.name;
                if (this.selectedIds.has(id)) {
                    this.selectedIds.delete(id);
                } else {
                    this.selectedIds.add(id);
                }
                
                this.$dispatch('selection-change', { 
                    selected: Array.from(this.selectedIds),
                    row 
                });
            },

            /**
             * Check if row is selected
             */
            isSelected(row) {
                const id = row.id || row.name;
                return this.selectedIds.has(id);
            },

            /**
             * Select all rows
             */
            onSelectAll() {
                if (!this.selectable) return;
                
                if (this.selectedIds.size === this.paginatedData.length) {
                    this.selectedIds.clear();
                } else {
                    this.paginatedData.forEach(row => {
                        this.selectedIds.add(row.id || row.name);
                    });
                }
                
                this.$dispatch('selection-change', { selected: Array.from(this.selectedIds) });
            },

            /**
             * Get all selected rows
             */
            getSelectedRows() {
                return this.data.filter(row => this.selectedIds.has(row.id || row.name));
            },

            /**
             * Clear selection
             */
            clearSelection() {
                this.selectedIds.clear();
            },

            /**
             * Handle row action
             */
            onAction(action, row, event) {
                event.stopPropagation();
                this.$dispatch('action', { action, row });
            },

            /**
             * Handle row click
             */
            onRowClick(row) {
                this.$dispatch('row-click', { row });
            },

            /**
             * Refresh data
             */
            async refresh() {
                this.loading = true;
                this.error = null;
                
                try {
                    if (options.onRefresh) {
                        const result = await options.onRefresh();
                        this.data = result.data || result;
                        this.total = result.total || this.data.length;
                    }
                } catch (err) {
                    this.error = err.message;
                } finally {
                    this.loading = false;
                }
            }
        };
    };

    /**
     * Data Table Template
     */
    global.AIDP.components.DataTableTemplate = `
        <div class="data-table">
            <!-- Toolbar -->
            <div x-show="searchable || $slots.toolbar" class="flex items-center justify-between mb-4">
                <div x-show="searchable" class="relative w-64">
                    <input type="text" 
                           x-model="searchQuery"
                           placeholder="搜索..."
                           class="w-full pl-9 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500">
                    <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs"></i>
                </div>
                <div x-html="$slots.toolbar ? $slots.toolbar : ''"></div>
            </div>

            <!-- Table -->
            <div class="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead class="bg-gray-800/50 text-gray-400 border-b border-gray-700">
                            <tr>
                                <!-- Select All -->
                                <th x-show="selectable" class="px-4 py-3 w-10">
                                    <input type="checkbox" 
                                           :checked="selectedIds.size === paginatedData.length && paginatedData.length > 0"
                                           @change="onSelectAll()"
                                           class="rounded border-gray-600 bg-gray-700 text-indigo-500 focus:ring-indigo-500">
                                </th>
                                
                                <!-- Column Headers -->
                                <template x-for="column in columns" :key="column.key">
                                    <th class="px-4 py-3 text-left font-medium whitespace-nowrap"
                                        :class="{ 'cursor-pointer hover:text-white': column.sortable }"
                                        @click="onSort(column)">
                                        <div class="flex items-center gap-1">
                                            <span x-text="column.title"></span>
                                            <i x-show="column.sortable" 
                                               class="fas text-xs"
                                               :class="getSortIcon(column)"></i>
                                        </div>
                                    </th>
                                </template>
                                
                                <!-- Actions -->
                                <th x-show="rowActions.length > 0" class="px-4 py-3 text-right">操作</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-700">
                            <!-- Loading State -->
                            <tr x-show="loading">
                                <td :colspan="columns.length + (selectable ? 1 : 0) + (rowActions.length > 0 ? 1 : 0)" 
                                    class="px-4 py-12 text-center text-gray-500">
                                    <i class="fas fa-spinner fa-spin text-2xl mb-2 block"></i>
                                    加载中...
                                </td>
                            </tr>
                            
                            <!-- Error State -->
                            <tr x-show="error && !loading">
                                <td :colspan="columns.length + (selectable ? 1 : 0) + (rowActions.length > 0 ? 1 : 0)" 
                                    class="px-4 py-12 text-center text-red-400">
                                    <i class="fas fa-exclamation-circle text-2xl mb-2 block"></i>
                                    <span x-text="error"></span>
                                </td>
                            </tr>
                            
                            <!-- Empty State -->
                            <tr x-show="!loading && !error && paginatedData.length === 0">
                                <td :colspan="columns.length + (selectable ? 1 : 0) + (rowActions.length > 0 ? 1 : 0)" 
                                    class="px-4 py-12 text-center text-gray-500">
                                    <i class="fas fa-inbox text-2xl mb-2 block"></i>
                                    暂无数据
                                </td>
                            </tr>
                            
                            <!-- Data Rows -->
                            <template x-for="row in paginatedData" :key="row.id || row.name">
                                <tr class="hover:bg-gray-700/30 transition cursor-pointer"
                                    :class="{ 'bg-indigo-500/5': isSelected(row) }"
                                    @click="onRowClick(row)">
                                    <!-- Selection Checkbox -->
                                    <td x-show="selectable" class="px-4 py-3" @click.stop>
                                        <input type="checkbox" 
                                               :checked="isSelected(row)"
                                               @change="onSelect(row)"
                                               class="rounded border-gray-600 bg-gray-700 text-indigo-500 focus:ring-indigo-500">
                                    </td>
                                    
                                    <!-- Cell Data -->
                                    <template x-for="column in columns" :key="column.key">
                                        <td class="px-4 py-3" :class="column.cellClass">
                                            <template x-if="column.template">
                                                <div x-html="column.template(row)"></div>
                                            </template>
                                            <template x-if="!column.template">
                                                <span class="text-gray-300" x-text="formatCell(getCellValue(row, column.key), column)"></span>
                                            </template>
                                        </td>
                                    </template>
                                    
                                    <!-- Row Actions -->
                                    <td x-show="rowActions.length > 0" class="px-4 py-3 text-right" @click.stop>
                                        <div class="flex items-center justify-end gap-1">
                                            <template x-for="action in rowActions" :key="action.name">
                                                <button @click="onAction(action.name, row, $event)"
                                                        :title="action.title || action.name"
                                                        class="p-1.5 rounded transition"
                                                        :class="action.class || 'text-gray-400 hover:text-white hover:bg-gray-700'">
                                                    <i class="fas" :class="action.icon"></i>
                                                </button>
                                            </template>
                                        </div>
                                    </td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Pagination -->
            <div x-show="pagination && totalPages > 1" class="flex items-center justify-between mt-4">
                <div class="text-sm text-gray-500">
                    显示 <span x-text="(page - 1) * pageSize + 1"></span> - 
                    <span x-text="Math.min(page * pageSize, processedData.length)"></span> 
                    条，共 <span x-text="processedData.length"></span> 条
                </div>
                
                <div class="flex items-center gap-2">
                    <button @click="onPageChange(page - 1)"
                            :disabled="page === 1"
                            class="px-3 py-1.5 bg-gray-700 border border-gray-600 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition">
                        <i class="fas fa-chevron-left"></i>
                    </button>
                    
                    <template x-for="p in totalPages" :key="p">
                        <button @click="onPageChange(p)"
                                :class="page === p ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
                                class="px-3 py-1.5 border border-gray-600 rounded-lg text-sm min-w-[2rem] transition">
                            <span x-text="p"></span>
                        </button>
                    </template>
                    
                    <button @click="onPageChange(page + 1)"
                            :disabled="page === totalPages"
                            class="px-3 py-1.5 bg-gray-700 border border-gray-600 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition">
                        <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

})(window);
