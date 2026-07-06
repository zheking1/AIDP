/**
 * AIDP Web UI - API Client Module
 * Standardized HTTP client for all API calls
 */

(function(global) {
    'use strict';

    const API_CONFIG = {
        baseUrl: '',
        timeout: 30000,
        retries: 3,
        retryDelay: 1000
    };

    class APIError extends Error {
        constructor(message, status, data) {
            super(message);
            this.name = 'APIError';
            this.status = status;
            this.data = data;
        }
    }

    class APIClient {
        constructor(config = {}) {
            this.config = { ...API_CONFIG, ...config };
            this.interceptors = {
                request: [],
                response: []
            };
        }

        /**
         * Add request interceptor
         */
        addRequestInterceptor(fn) {
            this.interceptors.request.push(fn);
        }

        /**
         * Add response interceptor
         */
        addResponseInterceptor(fn) {
            this.interceptors.response.push(fn);
        }

        /**
         * Execute request interceptors
         */
        async applyRequestInterceptors(url, options) {
            let result = { url, options };
            for (const interceptor of this.interceptors.request) {
                result = await interceptor(result.url, result.options) || result;
            }
            return result;
        }

        /**
         * Execute response interceptors
         */
        async applyResponseInterceptors(response) {
            let result = response;
            for (const interceptor of this.interceptors.response) {
                result = await interceptor(result) || result;
            }
            return result;
        }

        /**
         * Make HTTP request with retry logic
         */
        async request(method, endpoint, data = null, options = {}) {
            const url = `${this.config.baseUrl}${endpoint}`;
            const fetchOptions = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    ...options.headers
                },
                ...options
            };

            if (data && method !== 'GET') {
                fetchOptions.body = JSON.stringify(data);
            }

            // Apply request interceptors
            const intercepted = await this.applyRequestInterceptors(url, fetchOptions);

            let lastError;
            for (let attempt = 0; attempt < this.config.retries; attempt++) {
                try {
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);
                    
                    const response = await fetch(intercepted.url, {
                        ...intercepted.options,
                        signal: controller.signal
                    });
                    
                    clearTimeout(timeoutId);

                    // Apply response interceptors
                    const processedResponse = await this.applyResponseInterceptors(response);

                    if (!processedResponse.ok) {
                        const errorData = await processedResponse.json().catch(() => ({}));
                        throw new APIError(
                            errorData.message || `HTTP ${processedResponse.status}`,
                            processedResponse.status,
                            errorData
                        );
                    }

                    // Return null for 204 No Content
                    if (processedResponse.status === 204) {
                        return null;
                    }

                    return await processedResponse.json();
                } catch (error) {
                    lastError = error;
                    
                    // Don't retry on client errors (4xx)
                    if (error.status >= 400 && error.status < 500) {
                        throw error;
                    }

                    // Wait before retry
                    if (attempt < this.config.retries - 1) {
                        await this.delay(this.config.retryDelay * (attempt + 1));
                    }
                }
            }

            throw lastError;
        }

        /**
         * Delay helper
         */
        delay(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        // HTTP methods
        get(endpoint, options = {}) {
            return this.request('GET', endpoint, null, options);
        }

        post(endpoint, data, options = {}) {
            return this.request('POST', endpoint, data, options);
        }

        put(endpoint, data, options = {}) {
            return this.request('PUT', endpoint, data, options);
        }

        patch(endpoint, data, options = {}) {
            return this.request('PATCH', endpoint, data, options);
        }

        delete(endpoint, options = {}) {
            return this.request('DELETE', endpoint, null, options);
        }
    }

    // Create default instance
    const api = new APIClient();

    // Add auth interceptor
    api.addRequestInterceptor((url, options) => {
        // Add CSRF token if available
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        if (csrfToken) {
            options.headers['X-CSRF-Token'] = csrfToken;
        }
        return { url, options };
    });

    // Add error handling interceptor
    api.addResponseInterceptor(async (response) => {
        if (!response.ok) {
            // Log error for debugging
            console.error(`API Error: ${response.status} ${response.statusText}`);
        }
        return response;
    });

    // Export
    global.AIDP = global.AIDP || {};
    global.AIDP.API = api;
    global.AIDP.APIClient = APIClient;
    global.AIDP.APIError = APIError;

})(window);
