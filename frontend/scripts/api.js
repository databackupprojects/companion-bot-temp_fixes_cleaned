/**
 * API Helper Module
 * Handles all API calls to the backend
 */

const API_DEBUG = !!(typeof config !== 'undefined' && config?.features?.debugMode);

// Global logout handler - called when session expires
function handleSessionExpired() {
  if (API_DEBUG) {
    // eslint-disable-next-line no-console
    console.warn('[AUTH] Session expired - auto-logout triggered');
  }
  
  // Clear all auth data
  localStorage.removeItem('access_token');
  localStorage.removeItem('aiCompanionToken');
  localStorage.removeItem('aiCompanionData');
  localStorage.removeItem('dashboardSection');
  
  // Set logout timestamp to notify other tabs
  localStorage.setItem('logout_timestamp', Date.now().toString());
  
  // Show user message
  alert('Your session has expired. Please log in again.');
  
  // Redirect to home page
  window.location.href = 'index.html';
}

class APIClient {
  constructor() {
    this.baseURL = config.api.baseURL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
    this.token = localStorage.getItem('access_token');
  }

  /**
   * Set the auth token for subsequent requests
   */
  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('access_token', token);
    } else {
      localStorage.removeItem('access_token');
    }
  }

  /**
   * Get the current auth token
   */
  getToken() {
    return this.token || localStorage.getItem('access_token');
  }

  /**
   * Build request headers with auth if available
   */
  getHeaders(customHeaders = {}) {
    const headers = { ...this.defaultHeaders, ...customHeaders };
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  /**
   * Generic fetch wrapper with global auth error handling
   */
  async request(method, url, data = null, customHeaders = {}) {
    const options = {
      method,
      headers: this.getHeaders(customHeaders),
      credentials: 'include', // Include credentials for CORS requests
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      // Only stringify if data is not already a string
      options.body = typeof data === 'string' ? data : JSON.stringify(data);
    }

    if (API_DEBUG) {
      // eslint-disable-next-line no-console
      console.log(`[API] ${method} ${url}`, data ? 'with data:' : '', data);
    }
    
    try {
      // Create an AbortController for timeout handling
      const controller = new AbortController();
      // Increase timeout for DELETE requests (they may need to process database operations)
      const timeoutDuration = method === 'DELETE' ? 120000 : 60000; // 120 seconds for DELETE, 60 for others
      const timeoutId = setTimeout(() => controller.abort(), timeoutDuration);
      
      options.signal = controller.signal;
      
      const response = await fetch(url, options);
      clearTimeout(timeoutId); // Clear timeout if request completes
      if (API_DEBUG) {
        // eslint-disable-next-line no-console
        console.log(`[API] Response status: ${response.status}`);
      }
      
      const responseData = await response.json().catch(() => ({}));
      if (API_DEBUG) {
        // eslint-disable-next-line no-console
        console.log('[API] Response data:', responseData);
      }

      // Handle authentication errors globally - only 401 is session expiration
      if (response.status === 401) {
        if (API_DEBUG) {
          // eslint-disable-next-line no-console
          console.error(`[API] Session expired: ${response.status}`);
        }
        handleSessionExpired();
        return; // Stop execution - user will be redirected
      }

      if (!response.ok) {
        const error = {
          status: response.status,
          message: responseData.detail || responseData.message || 'API request failed',
          data: responseData,
        };
        if (API_DEBUG) {
          // eslint-disable-next-line no-console
          console.error('[API] Error thrown:', error);
        }
        throw error;
      }

      if (API_DEBUG) {
        // eslint-disable-next-line no-console
        console.log('[API] Success');
      }
      return responseData;
    } catch (error) {
      if (API_DEBUG) {
        // eslint-disable-next-line no-console
        console.error(`[API] Exception (${method} ${url}):`, error);
      }
      
      // Handle abort errors gracefully
      if (error.name === 'AbortError') {
        if (API_DEBUG) {
          // eslint-disable-next-line no-console
          console.warn('[API] Request timeout after ' + (method === 'DELETE' ? '120' : '60') + ' seconds');
        }
        throw {
          status: 408,
          message: 'Request timeout. The operation may still be processing.',
          data: {}
        };
      }
      
      throw error;
    }
  }

  /**
   * Authentication API calls
   */
  auth = {
    login: (email, password) =>
      this.request('POST', getApiUrl('auth', 'token'), 
        new URLSearchParams({ username: email, password }).toString(),
        { 'Content-Type': 'application/x-www-form-urlencoded' }
      ),

    register: (userData) =>
      this.request('POST', getApiUrl('auth', 'register'), userData),

    getCurrentUser: () =>
      this.request('GET', getApiUrl('auth', 'me')),

    refreshToken: () =>
      this.request('POST', getApiUrl('auth', 'refresh')),

    logout: () => {
      // Clear token from API client
      this.setToken(null);
      // Trigger global logout handler
      handleSessionExpired();
      return Promise.resolve();
    },
  };

  /**
   * Settings API calls
   */
  settings = {
    get: (userId = null) => {
      let url = getApiUrl('settings');
      if (userId) url += `?user_id=${userId}`;
      return this.request('GET', url);
    },

    update: (settings, userId = null) => {
      let url = getApiUrl('settings');
      if (userId) url += `?user_id=${userId}`;
      return this.request('PUT', url, settings);
    },

    getByUserId: (userId) =>
      this.request('GET', getApiUrl('settings', userId)),
  };

  /**
   * Messages API calls
   */
  messages = {
    send: (content, botId = null) => {
      const data = { message: content };
      if (botId) data.bot_id = botId;
      return this.request('POST', getApiUrl('messages'), data);
    },

    getHistory: (limit = 50, offset = 0, userId = null, botId = null) => {
      let url = `${getApiUrl('messages')}/history?limit=${limit}&offset=${offset}`;
      if (userId) url += `&user_id=${userId}`;
      if (botId) url += `&bot_id=${botId}`;
      return this.request('GET', url);
    },

    getByConversation: (conversationId) =>
      this.request('GET', getApiUrl('messages', conversationId)),

    clearHistory: (userId = null, botId = null) => {
      let url = `${getApiUrl('messages')}/clear`;
      if (userId) url += `?user_id=${encodeURIComponent(userId)}`;
      if (botId) url += (userId ? '&' : '?') + `bot_id=${botId}`;
      return this.request('DELETE', url);
    },
  };

  /**
   * Boundaries API calls
   */
  boundaries = {
    get: (userId = null) => {
      let url = getApiUrl('boundaries');
      if (userId) url += `?user_id=${userId}`;
      return this.request('GET', url);
    },

    create: (boundary, userId = null) => {
      let url = getApiUrl('boundaries');
      if (userId) url += `?user_id=${userId}`;
      return this.request('POST', url, boundary);
    },

    delete: (boundaryId, userId = null) => {
      let url = `${getApiUrl('boundaries')}/${boundaryId}`;
      if (userId) url += `?user_id=${userId}`;
      return this.request('DELETE', url);
    },

    update: (boundaryId, boundary, userId = null) => {
      let url = `${getApiUrl('boundaries')}/${boundaryId}`;
      if (userId) url += `?user_id=${userId}`;
      return this.request('PUT', url, boundary);
    },
  };

  /**
   * Analytics API calls
   */
  analytics = {
    getStats: (userId = null) => {
      let url = `${getApiUrl('messages')}/analytics`;
      if (userId) url += `?user_id=${userId}`;
      return this.request('GET', url);
    },
  };

  /**
   * Memory API calls
   */
  memory = {
    getSummary: (userId = null) => {
      let url = `${getApiUrl('messages')}/memory`;
      if (userId) url += `?user_id=${userId}`;
      return this.request('GET', url);
    },

    clear: (userId = null) => {
      let url = `${getApiUrl('messages')}/memory`;
      if (userId) url += `?user_id=${userId}`;
      return this.request('DELETE', url);
    },
  };

  /**
   * Admin API calls
   */
  admin = {
    getStats: () =>
      this.request('GET', getApiUrl('admin', 'stats')),

    getUsers: (page = 1, limit = 20) =>
      this.request('GET', `${getApiUrl('admin', 'users')}?page=${page}&limit=${limit}`),

    getUser: (userId) =>
      this.request('GET', getApiUrl('admin', `users/${userId}`)),

    updateUser: (userId, data) =>
      this.request('PUT', getApiUrl('admin', `users/${userId}`), data),

    banUser: (userId, reason) =>
      this.request('POST', getApiUrl('admin', `users/${userId}/ban`), { reason }),

    unbanUser: (userId) =>
      this.request('POST', getApiUrl('admin', `users/${userId}/unban`)),
  };

  /**
   * Quiz API calls
   */
  quiz = {
    getArchetypes: async () => {
      // For now, return config archetypes
      // Later this could be fetched from backend
      return config.quiz.archetypes;
    },

    saveResponse: (quizData) =>
      this.request('POST', getApiUrl('quiz', 'responses'), quizData),

    generateToken: (quizData) =>
      this.request('POST', getApiUrl('quiz', 'complete'), quizData),

    getQuizData: (token) =>
      this.request('GET', getApiUrl('quiz', `token/${token}`)),

    canCreateBot: () =>
      this.request('GET', getApiUrl('quiz', 'can-create')),
  };

  /**
   * Bots API calls
   */
  bots = {
    getAll: () =>
      this.request('GET', getApiUrl('bots')),

    get: (botId) =>
      this.request('GET', getApiUrl('bots', botId)),

    create: (botData) =>
      this.request('POST', getApiUrl('bots'), botData),

    update: (botId, botData) =>
      this.request('PUT', getApiUrl('bots', botId), botData),

    delete: (botId) =>
      this.request('DELETE', getApiUrl('bots', botId)),

    getTelegramLink: (botId) =>
      this.request('GET', getApiUrl('bots', `${botId}/telegram-link`)),
  };
}
// Create singleton instance
const api = new APIClient();
