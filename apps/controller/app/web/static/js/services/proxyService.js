/**
 * AIDP Web UI - Proxy Service
 * Handles proxying requests to individual tools
 */

(function(global) {
    'use strict';

    const { API, store, events, Events } = global.AIDP;

    class ProxyService {
        constructor() {
            this.activeProxies = new Map();
            this.rewriteRules = new Map();
        }

        /**
         * Get tool Web UI URL
         * @param {string} toolName - Tool name
         * @returns {string|null} Tool endpoint URL
         */
        getToolUrl(toolName) {
            const tools = store.get('tools.list') || [];
            const tool = tools.find(t => t.name === toolName);
            return tool?.endpoint || null;
        }

        /**
         * Check if tool has Web UI
         * @param {string} toolName - Tool name
         * @returns {boolean}
         */
        hasWebUI(toolName) {
            const url = this.getToolUrl(toolName);
            return !!url;
        }

        /**
         * Fetch tool page via proxy
         * @param {string} toolName - Tool name
         * @param {string} path - Path within tool (default: '/')
         * @param {Object} options - Fetch options
         * @returns {Promise<Object>} Response with content and metadata
         */
        async fetchToolPage(toolName, path = '/', options = {}) {
            const toolUrl = this.getToolUrl(toolName);
            
            if (!toolUrl) {
                throw new Error(`Tool not found: ${toolName}`);
            }

            // Use controller's proxy endpoint
            const proxyUrl = `/api/proxy/${toolName}${path}`;
            
            try {
                const response = await fetch(proxyUrl, {
                    method: options.method || 'GET',
                    headers: {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        ...options.headers
                    },
                    ...options
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const content = await response.text();
                const contentType = response.headers.get('content-type') || 'text/html';

                return {
                    content,
                    contentType,
                    status: response.status,
                    headers: Object.fromEntries(response.headers.entries())
                };
            } catch (error) {
                console.error(`Failed to fetch ${toolName}${path}:`, error);
                throw error;
            }
        }

        /**
         * Rewrite tool HTML for integration
         * - Removes conflicting headers/nav
         * - Rewrites links to use proxy
         * - Injects unified styles
         * @param {string} html - Original HTML
         * @param {string} toolName - Tool name
         * @param {string} basePath - Base path for link rewriting
         * @returns {string} Rewritten HTML
         */
        rewriteHTML(html, toolName, basePath = `/tools/${toolName}`) {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            // Remove conflicting elements
            const selectorsToRemove = [
                'nav', 'header', '.navbar', '.header', 
                '[role="navigation"]',
                '.sidebar:not(.keep-sidebar)'
            ];
            
            selectorsToRemove.forEach(selector => {
                doc.querySelectorAll(selector).forEach(el => {
                    // Don't remove if it contains essential tool controls
                    if (!el.querySelector('.tool-essential')) {
                        el.remove();
                    }
                });
            });

            // Rewrite links
            doc.querySelectorAll('a[href]').forEach(link => {
                const href = link.getAttribute('href');
                if (href && !href.startsWith('http') && !href.startsWith('#') && !href.startsWith('javascript:')) {
                    const newHref = this.rewriteLink(href, toolName, basePath);
                    link.setAttribute('href', newHref);
                }
            });

            // Rewrite form actions
            doc.querySelectorAll('form[action]').forEach(form => {
                const action = form.getAttribute('action');
                if (action && !action.startsWith('http')) {
                    form.setAttribute('action', this.rewriteLink(action, toolName, basePath));
                }
            });

            // Rewrite asset URLs (CSS, JS, images)
            const assetSelectors = [
                { selector: 'link[rel="stylesheet"]', attr: 'href' },
                { selector: 'script[src]', attr: 'src' },
                { selector: 'img[src]', attr: 'src' },
                { selector: 'source[src]', attr: 'src' }
            ];

            assetSelectors.forEach(({ selector, attr }) => {
                doc.querySelectorAll(selector).forEach(el => {
                    const url = el.getAttribute(attr);
                    if (url && !url.startsWith('http') && !url.startsWith('data:') && !url.startsWith('//')) {
                        const newUrl = this.rewriteAssetUrl(url, toolName);
                        el.setAttribute(attr, newUrl);
                    }
                });
            });

            // Inject unified styles
            const styleEl = doc.createElement('style');
            styleEl.textContent = this.getUnifiedStyles();
            doc.head.appendChild(styleEl);

            // Inject bridge script for cross-frame communication
            const bridgeScript = doc.createElement('script');
            bridgeScript.textContent = this.getBridgeScript(toolName);
            doc.head.appendChild(bridgeScript);

            return doc.documentElement.outerHTML;
        }

        /**
         * Rewrite a link to use proxy
         */
        rewriteLink(href, toolName, basePath) {
            // Absolute paths
            if (href.startsWith('/')) {
                return `${basePath}${href}`;
            }
            // Relative paths
            return `${basePath}/${href}`;
        }

        /**
         * Rewrite asset URL
         */
        rewriteAssetUrl(url, toolName) {
            const toolUrl = this.getToolUrl(toolName);
            if (!toolUrl) return url;

            // Absolute path from tool root
            if (url.startsWith('/')) {
                return `/api/proxy/${toolName}${url}`;
            }

            // Relative path - resolve against tool base
            return `/api/proxy/${toolName}/${url}`;
        }

        /**
         * Get unified styles to inject
         */
        getUnifiedStyles() {
            return `
                /* AIDP Unified UI Styles */
                body {
                    background-color: #111827 !important;
                    color: #f3f4f6 !important;
                }
                
                /* Hide tool-specific navigation when embedded */
                body.aidp-embedded nav,
                body.aidp-embedded .navbar,
                body.aidp-embedded header:not(.tool-content header) {
                    display: none !important;
                }
                
                /* Ensure tool content is full width */
                body.aidp-embedded .container,
                body.aidp-embedded main {
                    max-width: 100% !important;
                    padding: 0 !important;
                }
            `;
        }

        /**
         * Get bridge script for tool integration
         */
        getBridgeScript(toolName) {
            return `
                (function() {
                    // Mark as embedded
                    document.body.classList.add('aidp-embedded');
                    
                    // Notify parent frame of ready state
                    window.parent.postMessage({
                        type: 'aidp:tool:ready',
                        tool: '${toolName}'
                    }, '*');
                    
                    // Intercept navigation
                    document.addEventListener('click', function(e) {
                        const link = e.target.closest('a');
                        if (link && link.href && !link.href.startsWith('javascript:')) {
                            // Let parent handle navigation
                            window.parent.postMessage({
                                type: 'aidp:tool:navigate',
                                tool: '${toolName}',
                                href: link.getAttribute('href')
                            }, '*');
                        }
                    });
                })();
            `;
        }

        /**
         * Load tool in iframe mode
         * @param {string} toolName - Tool name
         * @param {HTMLElement} container - Container element
         * @param {Object} options - Load options
         */
        async loadToolInIframe(toolName, container, options = {}) {
            const toolUrl = this.getToolUrl(toolName);
            
            if (!toolUrl) {
                container.innerHTML = this.getErrorHTML(`Tool not found: ${toolName}`);
                return;
            }

            const { path = '/', onLoad, onError } = options;

            // Create iframe
            const iframe = document.createElement('iframe');
            iframe.src = `/api/proxy/${toolName}${path}`;
            iframe.className = 'w-full h-full border-0';
            iframe.style.minHeight = options.minHeight || '600px';
            
            iframe.onload = () => {
                onLoad?.(iframe);
            };
            
            iframe.onerror = (error) => {
                onError?.(error);
                container.innerHTML = this.getErrorHTML(`Failed to load ${toolName}`);
            };

            container.innerHTML = '';
            container.appendChild(iframe);

            // Track active proxy
            this.activeProxies.set(toolName, { iframe, container });

            return iframe;
        }

        /**
         * Load tool with content rewriting
         * @param {string} toolName - Tool name
         * @param {HTMLElement} container - Container element
         * @param {Object} options - Load options
         */
        async loadToolWithRewrite(toolName, container, options = {}) {
            const { path = '/' } = options;

            try {
                const response = await this.fetchToolPage(toolName, path);
                const rewritten = this.rewriteHTML(response.content, toolName);
                
                container.innerHTML = rewritten;
                
                // Execute scripts in rewritten content
                this.executeScripts(container);
                
            } catch (error) {
                console.error('Failed to load tool:', error);
                container.innerHTML = this.getErrorHTML(error.message);
            }
        }

        /**
         * Execute scripts in container
         */
        executeScripts(container) {
            const scripts = container.querySelectorAll('script');
            scripts.forEach(oldScript => {
                const newScript = document.createElement('script');
                
                // Copy attributes
                Array.from(oldScript.attributes).forEach(attr => {
                    newScript.setAttribute(attr.name, attr.value);
                });
                
                // Copy content
                newScript.textContent = oldScript.textContent;
                
                // Replace
                oldScript.parentNode.replaceChild(newScript, oldScript);
            });
        }

        /**
         * Get error HTML
         */
        getErrorHTML(message) {
            return `
                <div class="flex items-center justify-center h-64 text-gray-500">
                    <div class="text-center">
                        <i class="fas fa-exclamation-circle text-4xl mb-3 text-red-400"></i>
                        <p class="text-lg">${message}</p>
                        <button onclick="location.reload()" class="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
                            <i class="fas fa-redo mr-2"></i>Retry
                        </button>
                    </div>
                </div>
            `;
        }

        /**
         * Get tool info for display
         * @param {string} toolName - Tool name
         * @returns {Object|null} Tool info
         */
        getToolInfo(toolName) {
            const tools = store.get('tools.list') || [];
            const tool = tools.find(t => t.name === toolName);
            
            if (!tool) return null;

            return {
                ...tool,
                webUIAvailable: this.hasWebUI(toolName),
                healthStatus: tool.status,
                lastCheck: tool.lastHealthCheck
            };
        }

        /**
         * Refresh all active proxies
         */
        refreshAll() {
            this.activeProxies.forEach(({ iframe }, toolName) => {
                if (iframe.contentWindow) {
                    iframe.contentWindow.location.reload();
                }
            });
        }

        /**
         * Cleanup proxy resources
         * @param {string} toolName - Tool name (optional, cleans all if not specified)
         */
        cleanup(toolName) {
            if (toolName) {
                const proxy = this.activeProxies.get(toolName);
                if (proxy) {
                    proxy.iframe.remove();
                    this.activeProxies.delete(toolName);
                }
            } else {
                this.activeProxies.forEach(({ iframe }) => iframe.remove());
                this.activeProxies.clear();
            }
        }
    }

    // Create singleton instance
    const proxyService = new ProxyService();

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        proxyService.cleanup();
    });

    // Handle messages from embedded tools
    window.addEventListener('message', (event) => {
        const { data } = event;
        
        if (data?.type?.startsWith('aidp:')) {
            events.emit(data.type, data);
            
            // Handle navigation
            if (data.type === 'aidp:tool:navigate') {
                window.location.href = data.href;
            }
        }
    });

    // Export
    global.AIDP = global.AIDP || {};
    global.AIDP.ProxyService = ProxyService;
    global.AIDP.proxyService = proxyService;

})(window);
