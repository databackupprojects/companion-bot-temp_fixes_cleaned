/**
 * Frontend Configuration
 *
 * NOTE:
 * - Do not hard-code localhost only.
 * - Allow overrides via:
 *   1) window.__API_BASE_URL__
 *   2) <meta name="api-base-url" content="...">
 *   3) localStorage("api_base_url")
 *   4) query param: ?apiBase=https://...
 * - Fallbacks:
 *   - localhost -> http://localhost:8010
 *   - production -> https://bot_api.martofpk.com
 */

function normalizeBaseUrl(url) {
  if (!url || typeof url !== 'string') return null;
  const trimmed = url.trim();
  if (!trimmed) return null;
  return trimmed.replace(/\/+$/, '');
}

function resolveApiBaseUrl() {
  // Highest priority: URL param to simplify debugging without code changes.
  const params = new URLSearchParams(window.location.search);
  const fromQuery = normalizeBaseUrl(params.get('apiBase'));
  if (fromQuery) return fromQuery;

  const fromWindow = normalizeBaseUrl(window.__API_BASE_URL__);
  if (fromWindow) return fromWindow;

  const meta = document.querySelector('meta[name="api-base-url"]');
  const fromMeta = normalizeBaseUrl(meta?.getAttribute('content'));
  if (fromMeta) return fromMeta;

  const fromStorage = normalizeBaseUrl(localStorage.getItem('api_base_url'));
  if (fromStorage) return fromStorage;

  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    // Default to the local API port used by this project
    return 'http://localhost:8000';
  }

  return 'http://localhost:8000';
}

const API_BASE_URL = resolveApiBaseUrl();
const ENVIRONMENT = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'development'
  : 'production';

// Individual Telegram bots per archetype
const TELEGRAM_BOTS = {
  golden_retriever: 'golden_retriever_bot',
  tsundere: 'tsundere_bot',
  lawyer: 'lawyer_bot',
  cool_girl: 'cool_girl_bot',
  toxic_ex: 'toxic_ex_bot',
};

const config = {
  // API Configuration
  api: {
    baseURL: API_BASE_URL,
    endpoints: {
      auth: `${API_BASE_URL}/api/auth`,
      settings: `${API_BASE_URL}/api/settings`,
      messages: `${API_BASE_URL}/api/messages`,
      boundaries: `${API_BASE_URL}/api/boundaries`,
      admin: `${API_BASE_URL}/api/admin`,
      quiz: `${API_BASE_URL}/api/quiz`,
      bots: `${API_BASE_URL}/api/bots`,
    }
  },

  // Telegram Configuration
  telegram: {
    bots: TELEGRAM_BOTS,
    // Get bot username for a specific archetype
    getBotUsername: (archetype) => TELEGRAM_BOTS[archetype] || TELEGRAM_BOTS.golden_retriever,
    // Get deep link for a specific archetype and token
    getDeepLink: (archetype, token) => {
      const botUsername = TELEGRAM_BOTS[archetype] || TELEGRAM_BOTS.golden_retriever;
      return `https://t.me/${botUsername}?start=${token}`;
    },
  },

  // Environment
  environment: ENVIRONMENT,
  isDevelopment: ENVIRONMENT === 'development',
  isProduction: ENVIRONMENT === 'production',

  // Feature Flags
  features: {
    analyticsEnabled: true,
    debugMode: ENVIRONMENT === 'development',
  },

  // UI Configuration
  ui: {
    toastDuration: 3000,
    animationDuration: 300,
    maxMessageLength: 4000,
  },

  // Quiz Configuration (from spec)
  quiz: {
    steps: 8,
    archetypes: [
      {
        id: 'golden_retriever',
        name: 'Golden Retriever',
        emoji: '🐕‍🦺',
        description: 'Your biggest fan — unconditional support',
      },
      {
        id: 'tsundere',
        name: 'Tsundere',
        emoji: '😤→😊',
        description: 'Earning affection — plays hard to get',
      },
      {
        id: 'lawyer',
        name: 'Lawyer',
        emoji: '⚖️',
        description: 'Intellectual sparring — challenges you',
      },
      {
        id: 'cool_girl',
        name: 'Cool Girl',
        emoji: '😎',
        description: 'Chase dynamic — effortlessly desirable',
      },
      {
        id: 'toxic_ex',
        name: 'Toxic Ex',
        emoji: '🔥',
        description: 'Drama/intensity — emotional rollercoaster',
      },
    ],
    genders: [
      { id: 'female', label: 'Her' },
      { id: 'male', label: 'Him' },
      { id: 'nonbinary', label: 'Them' },
    ],
    attachmentStyles: [
      {
        id: 'secure',
        label: '💚 Secure',
        description: 'Comfortable with intimacy. Responds consistently. Healthy communication.',
      },
      {
        id: 'anxious',
        label: '💛 Anxious',
        description: 'Wants reassurance. Texts back fast. Gets worried if you\'re distant.',
      },
      {
        id: 'avoidant',
        label: '💙 Avoidant',
        description: 'Values independence. Pulls back when things get intense. Hard to reach.',
      },
    ],
    flirtinessLevels: [
      { id: 'none', label: 'None — Keep it friendly' },
      { id: 'subtle', label: 'Subtle — Occasional hints' },
      { id: 'flirty', label: 'Flirty — Openly playful' },
    ],
    toxicityLevels: [
      { id: 'healthy', label: 'Healthy — Supportive and wholesome' },
      { id: 'mild', label: 'Mild — Light teasing, playful jealousy' },
      { id: 'toxic_light', label: 'Spicy — Push-pull dynamics, drama' },
    ],
  },

  // Message Limits (from spec)
  messageLimits: {
    free: 20,
    plus: 200,
    premium: 1000,
  },

  // Default Bot Settings
  defaultBotSettings: {
    bot_name: 'Dot',
    bot_gender: 'female',
    archetype: 'golden_retriever',
    attachment_style: 'secure',
    flirtiness: 'subtle',
    toxicity: 'healthy',
  },
};

/**
 * Utility function to construct API URLs
 * Usage: getApiUrl('auth', 'token') => http://localhost:8001/api/auth/token
 */
function getApiUrl(resource, endpoint = null) {
  const baseUrl = config.api.endpoints[resource];
  if (!baseUrl) {
    console.warn(`Unknown resource: ${resource}`);
    return config.api.baseURL;
  }
  return endpoint ? `${baseUrl}/${endpoint}` : baseUrl;
}

// Log configuration only when explicitly in debug.
if (config.features.debugMode) {
  // eslint-disable-next-line no-console
  console.log('[CONFIG] Frontend configuration loaded', {
    environment: config.environment,
    apiBaseUrl: config.api.baseURL,
  });
}
