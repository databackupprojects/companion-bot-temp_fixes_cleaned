// ===== FILE: scripts/dashboard.js =====

// Use API_BASE_URL from config.js
// Note: config is already defined in config.js
let currentUser = null;
let currentPersona = null;
let userBots = [];  // Array to store all user's bots
let activeBotIndex = 0;  // Index of currently active bot
let currentBotId = null;  // ID of currently selected bot for chat
let isLoggingOut = false; // flag to prevent double logout

const DASH_DEBUG = !!(typeof config !== 'undefined' && config?.features?.debugMode);
function dashLog(...args) {
    if (DASH_DEBUG) {
        // eslint-disable-next-line no-console
        console.log(...args);
    }
}

// DOM Elements
let elements = {};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeElements();
    setupEventListeners();

    // On smaller screens, start with sidebar hidden.
    // `collapsed` means hidden across the CSS.
    const sidebar = document.querySelector('.sidebar');
    if (sidebar && window.innerWidth <= 1024) {
        sidebar.classList.add('collapsed');
        const icon = document.getElementById('sidebarToggle')?.querySelector('i');
        if (icon) icon.className = 'fas fa-bars';
    }

    checkAuthAndLoadData();
    
    // Listen for logout events from other tabs
    window.addEventListener('storage', function(e) {
        if (e.key === 'logout_timestamp') {
            dashLog('[AUTH] Logout detected from another tab');
            // Token was cleared from another tab, redirect to home
            localStorage.removeItem('access_token');
            window.location.href = 'index.html';
        }
    });
});

function initializeElements() {
    // Cache DOM elements for better performance
    elements = {
        // Sidebar
        dashboardUserName: document.getElementById('dashboardUserName'),
        userTier: document.getElementById('userTier'),
        sidebarToggle: document.getElementById('sidebarToggle'),
        sidebarBackdrop: document.getElementById('sidebarBackdrop'),
        
        // Daily Limits
        messagesCount: document.getElementById('messagesCount'),
        proactiveCount: document.getElementById('proactiveCount'),
        messagesProgress: document.getElementById('messagesProgress'),
        proactiveProgress: document.getElementById('proactiveProgress'),
        
        // Chat
        pageTitle: document.getElementById('pageTitle'),
        pageSubtitle: document.getElementById('pageSubtitle'),
        chatMessages: document.getElementById('chatMessages'),
        messageInput: document.getElementById('messageInput'),
        charCount: document.getElementById('charCount'),
        dailyCount: document.getElementById('dailyCount'),
        newChatBtn: document.getElementById('newChatBtn'),
        refreshBtn: document.getElementById('refreshBtn'),
        
        // Companion Info
        companionAvatar: document.getElementById('companionAvatar'),
        companionName: document.getElementById('companionName'),
        companionArchetype: document.getElementById('companionArchetype'),
        companionStatus: document.getElementById('companionStatus'),
        
        // Settings
        settingBotName: document.getElementById('settingBotName'),
        settingGender: document.getElementById('settingGender'),
        settingArchetype: document.getElementById('settingArchetype'),
        settingAttachment: document.getElementById('settingAttachment'),
        settingFlirtiness: document.getElementById('settingFlirtiness'),
        settingToxicity: document.getElementById('settingToxicity'),
        advancedSettings: document.getElementById('advancedSettings'),
        
        // Boundaries
        boundariesList: document.getElementById('boundariesList'),
        boundaryType: document.getElementById('boundaryType'),
        boundaryValue: document.getElementById('boundaryValue'),
        boundaryHint: document.getElementById('boundaryHint'),
        
        // Analytics
        totalMessages: document.getElementById('totalMessages'),
        activeDays: document.getElementById('activeDays'),
        avgLength: document.getElementById('avgLength'),
        commonMood: document.getElementById('commonMood'),
        messagesChart: document.getElementById('messagesChart'),
        moodChart: document.getElementById('moodChart'),
        activityList: document.getElementById('activityList'),
        
        // Memory
        memoryCount: document.getElementById('memoryCount'),
        memoryCategories: document.getElementById('memoryCategories'),
        memoryImportance: document.getElementById('memoryImportance'),
        categoryTabs: document.getElementById('categoryTabs'),
        memoriesList: document.getElementById('memoriesList'),
        
        // Modals
        supportModal: document.getElementById('supportModal'),
        loadingOverlay: document.getElementById('loadingOverlay')
    };
}

function setupEventListeners() {
    // Sidebar toggle
    if (elements.sidebarToggle) {
        elements.sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    // Mobile menu toggle
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', toggleSidebar);
    }
    
    // Close sidebar when clicking backdrop
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');
    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', function() {
            dashLog('[sidebarBackdrop] Clicked, closing sidebar');
            toggleSidebar();
        });
    }
    
    // Nav items - use event delegation for section navigation
    const sidebarNav = document.querySelector('.sidebar-nav');
    if (sidebarNav) {
        sidebarNav.addEventListener('click', function(e) {
            const navItem = e.target.closest('.nav-item');
            if (!navItem) return;
            
            const section = navItem.dataset.section;
            if (section) {
                e.preventDefault();
                navigateToSection(section);
            }
            
            const windowWidth = window.innerWidth;
            const sidebar = document.querySelector('.sidebar');
            
            // Close sidebar on mobile after clicking nav item
            if (windowWidth <= 1024 && sidebar && !sidebar.classList.contains('collapsed')) {
                dashLog('[navItem] Mobile - closing sidebar after navigation');
                sidebar.classList.add('collapsed');
                const icon = elements.sidebarToggle ? elements.sidebarToggle.querySelector('i') : null;
                if (icon) {
                    icon.className = 'fas fa-bars';
                }
                // Remove backdrop
                if (elements.sidebarBackdrop) {
                    elements.sidebarBackdrop.classList.remove('active');
                }
            }
        });
    }
    
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }
    
    // Chat input
    if (elements.messageInput) {
        elements.messageInput.addEventListener('input', updateCharCount);
        elements.messageInput.addEventListener('keypress', handleMessageKeypress);
    }
    
    // Send button
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.addEventListener('click', function(e) {
            e.preventDefault();
            sendMessage();
        });
    }
    
    // Chat buttons
    if (elements.newChatBtn) {
        elements.newChatBtn.addEventListener('click', startNewChat);
    }
    
    if (elements.refreshBtn) {
        elements.refreshBtn.addEventListener('click', refreshChat);
    }
    
    // Chat header action buttons
    const chatSettingsBtn = document.getElementById('chatSettingsBtn');
    if (chatSettingsBtn) {
        chatSettingsBtn.addEventListener('click', showSettings);
    }
    
    const clearChatBtn = document.getElementById('clearChatBtn');
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', clearChat);
    }
    
    const helpBtn = document.getElementById('helpBtn');
    if (helpBtn) {
        helpBtn.addEventListener('click', showSupport);
    }
    
    const sayHelloBtn = document.getElementById('sayHelloBtn');
    if (sayHelloBtn) {
        sayHelloBtn.addEventListener('click', sendFirstMessage);
    }
    
    // Settings buttons
    const reloadSettingsBtn = document.getElementById('reloadSettingsBtn');
    if (reloadSettingsBtn) {
        reloadSettingsBtn.addEventListener('click', loadSettings);
    }
    
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', saveSettings);
    }
    
    if (document.getElementById('resetAdvancedSettingsBtn')) {
        const resetBtn = document.getElementById('resetAdvancedSettingsBtn');
        resetBtn.addEventListener('click', function(e) {
            e.preventDefault();
            resetAdvancedSettings();
        });
    }
    
    // Bots management - Redirect to quiz instead of opening modal
    const createBotBtn = document.getElementById('createBotBtn');
    if (createBotBtn) {
        createBotBtn.addEventListener('click', () => {
            // Redirect to quiz page to create new bot
            window.location.href = 'quiz.html';
        });
    }
    
    // Bot selector in chat section
    const chatBotSelect = document.getElementById('chatBotSelect');
    if (chatBotSelect) {
        chatBotSelect.addEventListener('change', async (e) => {
            const botId = e.target.value;
            if (botId) {
                currentBotId = botId;
                await switchChatBot(botId);
            }
        });
    }
    
    // Boundaries
    const addBoundaryBtn = document.getElementById('addBoundaryBtn');
    dashLog('[setupEventListeners] addBoundaryBtn found:', !!addBoundaryBtn);
    
    if (addBoundaryBtn) {
        addBoundaryBtn.addEventListener('click', function(e) {
            e.preventDefault();
            addBoundary();
        });
    } else {
        if (DASH_DEBUG) {
            // eslint-disable-next-line no-console
            console.warn('[setupEventListeners] addBoundaryBtn not found; skipping handler');
        }
        // Fallback: Try again after a delay
        setTimeout(() => {
            const delayedBtn = document.getElementById('addBoundaryBtn');
            dashLog('[setupEventListeners] Delayed check - addBoundaryBtn found:', !!delayedBtn);
            if (delayedBtn) {
                delayedBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    addBoundary();
                });
            }
        }, 1000);
    }
    
    // Boundary toggle and delete - use event delegation
    if (elements.boundariesList) {
        elements.boundariesList.addEventListener('click', function(e) {
            const toggleBtn = e.target.closest('.toggle-boundary');
            if (toggleBtn) {
                dashLog('[boundariesList] Toggle button clicked');
                const boundaryItem = toggleBtn.closest('[data-id]');
                if (boundaryItem) {
                    const id = boundaryItem.dataset.id;
                    dashLog('[boundariesList] Toggling boundary:', id);
                    toggleBoundary(id);
                }
            }
            
            const deleteBtn = e.target.closest('.delete-boundary');
            if (deleteBtn) {
                dashLog('[boundariesList] Delete button clicked');
                const boundaryItem = deleteBtn.closest('[data-id]');
                if (boundaryItem) {
                    const id = boundaryItem.dataset.id;
                    dashLog('[boundariesList] Deleting boundary:', id);
                    deleteBoundary(id);
                }
            }
        });
    }
    
    // Memory buttons
    const refreshMemoryBtn = document.getElementById('refreshMemoryBtn');
    if (refreshMemoryBtn) {
        refreshMemoryBtn.addEventListener('click', refreshMemory);
    }
    
    const clearMemoryBtn = document.getElementById('clearMemoryBtn');
    if (clearMemoryBtn) {
        clearMemoryBtn.addEventListener('click', clearMemory);
    }
    
    // Upgrade buttons - use event delegation
    document.querySelectorAll('[data-upgrade]').forEach(btn => {
        btn.addEventListener('click', function() {
            upgradeTo(this.dataset.upgrade);
        });
    });
    
    // Boundary type change
    if (elements.boundaryType) {
        elements.boundaryType.addEventListener('change', updateBoundaryHint);
    }
    
    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').classList.remove('active');
        });
    });
    
    // Support modal buttons
    const closeSupportModalBtn = document.getElementById('closeSupportModalBtn');
    if (closeSupportModalBtn) {
        closeSupportModalBtn.addEventListener('click', closeSupportModal);
    }
    
    const closeSupportModalBtn2 = document.getElementById('closeSupportModalBtn2');
    if (closeSupportModalBtn2) {
        closeSupportModalBtn2.addEventListener('click', closeSupportModal);
    }
    
    const sendSupportMessageBtn = document.getElementById('sendSupportMessageBtn');
    if (sendSupportMessageBtn) {
        sendSupportMessageBtn.addEventListener('click', sendSupportMessage);
    }
}

async function checkAuthAndLoadData() {
    showLoading();
    
    try {
            // Check if user is authenticated
        const token = localStorage.getItem('access_token');
        if (!token) {
            window.location.href = 'index.html';
            return;
        }
        
        // Set token in API client
        api.setToken(token);
        
        // Get user data using API module
        // Global 401/403 handler in api.js will auto-logout if session expired
        currentUser = await api.auth.getCurrentUser();
        
        updateUserUI();
        
        // Get persona data
        await loadPersonaData();
        
        // Load initial data based on saved section or current section
        let sectionId = localStorage.getItem('dashboardSection') || 'chat';
        
        // If saved section is not 'chat', navigate to it
        if (sectionId !== 'chat') {
            navigateToSection(sectionId);
        }
        
        await loadSectionData(sectionId);
        
    } catch (error) {
        console.error('❌ Error loading dashboard:', error);
        showError('Failed to load dashboard. Please try refreshing.');
    } finally {
        hideLoading();
    }
}

function updateUserUI() {
    if (!currentUser) return;
    
    // Update user info
    if (elements.dashboardUserName) {
        elements.dashboardUserName.textContent = currentUser.name || currentUser.email || 'User';
    }
    
    if (elements.userTier) {
        elements.userTier.textContent = currentUser.tier || 'Free';
        elements.userTier.className = `tier-badge ${currentUser.tier || 'free'}`;
    }
    
    // Show admin panel link if user is admin
    if (currentUser.role === 'admin') {
        const adminLink = document.getElementById('adminPanelLink');
        if (adminLink) {
            adminLink.style.display = 'flex';
        }
    }
    
    // Update daily limits
    if (currentUser.limits) {
        const { messages_today, proactive_today, daily_message_limit, daily_proactive_limit } = currentUser.limits;
        
        if (elements.messagesCount) {
            elements.messagesCount.textContent = `${messages_today || 0}/${daily_message_limit || 20}`;
        }
        
        if (elements.proactiveCount) {
            elements.proactiveCount.textContent = `${proactive_today || 0}/${daily_proactive_limit || 1}`;
        }
        
        if (elements.messagesProgress) {
            const progress = ((messages_today || 0) / (daily_message_limit || 20)) * 100;
            elements.messagesProgress.style.width = `${Math.min(progress, 100)}%`;
        }
        
        if (elements.proactiveProgress) {
            const progress = ((proactive_today || 0) / (daily_proactive_limit || 1)) * 100;
            elements.proactiveProgress.style.width = `${Math.min(progress, 100)}%`;
        }
        
        if (elements.dailyCount) {
            elements.dailyCount.textContent = `${messages_today || 0} messages today`;
        }
    }
}

async function loadPersonaData() {
    try {
        // Load all user's bots from API
        const response = await fetch(`${config.api.baseURL}/api/quiz/my-bots`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            userBots = data.bots || [];
            
            if (userBots.length > 0) {
                // Show bot tabs if user has multiple bots (or is premium tier)
                const botTabsContainer = document.getElementById('botTabsContainer');
                if (userBots.length > 1 || currentUser.tier === 'premium') {
                    if (botTabsContainer) {
                        botTabsContainer.style.display = 'flex';
                        renderBotTabs();
                    }
                }
                
                // Load the first bot or previously active bot
                const savedBotIndex = localStorage.getItem('activeBotIndex');
                activeBotIndex = savedBotIndex ? parseInt(savedBotIndex) : 0;
                
                if (activeBotIndex >= userBots.length) {
                    activeBotIndex = 0;
                }
                
                currentPersona = userBots[activeBotIndex];
                updatePersonaUI();
            } else {
                // Fallback to localStorage
                const personaData = JSON.parse(localStorage.getItem('aiCompanionData'));
                if (personaData) {
                    currentPersona = personaData;
                    updatePersonaUI();
                }
            }
        } else {
            // Fallback to localStorage
            const personaData = JSON.parse(localStorage.getItem('aiCompanionData'));
            if (personaData) {
                currentPersona = personaData;
                updatePersonaUI();
            }
        }
        
    } catch (error) {
        console.error('Error loading persona:', error);
        // Use default persona
        currentPersona = {
            bot_name: 'Dot',
            bot_gender: 'female',
            archetype: 'golden_retriever',
            attachment_style: 'secure',
            flirtiness: 'subtle',
            toxicity: 'healthy'
        };
        updatePersonaUI();
    }
}

function renderBotTabs() {
    const botTabs = document.getElementById('botTabs');
    if (!botTabs) return;
    
    botTabs.innerHTML = '';
    
    userBots.forEach((bot, index) => {
        const tab = document.createElement('div');
        tab.className = 'bot-tab' + (index === activeBotIndex ? ' active' : '');
        tab.dataset.botIndex = index;
        
        const archetypeColors = {
            'golden_retriever': '#fbbf24',
            'tsundere': '#38bdf8',
            'lawyer': '#8b5cf6',
            'cool_girl': '#06b6d4',
            'toxic_ex': '#ec4899'
        };
        
        const archetypeIcons = {
            'golden_retriever': '🐕',
            'tsundere': '😤',
            'lawyer': '⚖️',
            'cool_girl': '😎',
            'toxic_ex': '🔥'
        };
        
        const color = archetypeColors[bot.archetype] || '#6366f1';
        const icon = archetypeIcons[bot.archetype] || '🤖';
        
        tab.innerHTML = `
            <div class="bot-tab-icon" style="background: ${color}20; color: ${color};">
                ${icon}
            </div>
            <span class="bot-tab-name">${bot.bot_name}</span>
        `;
        
        tab.addEventListener('click', () => switchBot(index));
        botTabs.appendChild(tab);
    });
    
    // Add event listener for create new bot button
    const createNewBotBtn = document.getElementById('createNewBotBtn');
    if (createNewBotBtn) {
        createNewBotBtn.onclick = async () => {
            try {
                showLoading();
                const response = await api.quiz.canCreateBot();
                
                console.log('[Dashboard] canCreateBot response:', response);
                
                if (!response.can_create) {
                    showError(response.message || 'You have reached your bot creation limit. Upgrade to Premium tier to create more bots.');
                    hideLoading();
                    return;
                }
                
                // Store tier info and used archetypes in sessionStorage for quiz page
                sessionStorage.setItem('user_tier', response.tier);
                const usedArchetypesJSON = JSON.stringify(response.used_archetypes || []);
                sessionStorage.setItem('used_archetypes', usedArchetypesJSON);
                
                console.log('[Dashboard] Set sessionStorage used_archetypes:', usedArchetypesJSON);
                
                hideLoading();
                window.location.href = 'quiz.html';
            } catch (error) {
                console.error('Error checking bot creation quota:', error);
                showError('Failed to check bot creation quota. Please try again.');
                hideLoading();
            }
        };
    }
}

function switchBot(index) {
    if (index < 0 || index >= userBots.length) return;
    
    activeBotIndex = index;
    localStorage.setItem('activeBotIndex', activeBotIndex);
    
    currentPersona = userBots[activeBotIndex];
    updatePersonaUI();
    renderBotTabs();
    
    // Reload chat for the new bot
    loadChatHistory();
}

function updatePersonaUI() {
    if (!currentPersona) return;
    
    // Update companion info in chat
    if (elements.companionName) {
        elements.companionName.textContent = currentPersona.bot_name || 'Companion';
    }
    
    if (elements.companionArchetype) {
        const archetypeNames = {
            'golden_retriever': 'Golden Retriever',
            'tsundere': 'Tsundere',
            'lawyer': 'Lawyer',
            'cool_girl': 'Cool Girl',
            'toxic_ex': 'Toxic Ex'
        };
        elements.companionArchetype.textContent = archetypeNames[currentPersona.archetype] || currentPersona.archetype;
    }
    
    if (elements.companionAvatar) {
        const avatarColors = {
            'golden_retriever': 'linear-gradient(135deg, #fbbf24, #f59e0b)',
            'tsundere': 'linear-gradient(135deg, #38bdf8, #0ea5e9)',
            'lawyer': 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
            'cool_girl': 'linear-gradient(135deg, #06b6d4, #0891b2)',
            'toxic_ex': 'linear-gradient(135deg, #ec4899, #db2777)'
        };
        elements.companionAvatar.style.background = avatarColors[currentPersona.archetype] || avatarColors.golden_retriever;
    }
    
    // Update settings form
    if (elements.settingBotName) {
        elements.settingBotName.value = currentPersona.bot_name || '';
    }
    
    if (elements.settingGender) {
        elements.settingGender.value = currentPersona.bot_gender || 'female';
    }
    
    if (elements.settingArchetype) {
        const currentArchetype = currentPersona.archetype || 'golden_retriever';
        elements.settingArchetype.value = currentArchetype;
        
        // Disable all archetype options except the current one
        const options = elements.settingArchetype.querySelectorAll('option');
        options.forEach(option => {
            if (option.value !== currentArchetype) {
                option.disabled = true;
                option.textContent = option.textContent + ' (Upgrade to use)';
            }
        });
        
        // Remove any existing change listeners to avoid duplicates
        const newSelect = elements.settingArchetype.cloneNode(true);
        elements.settingArchetype.parentNode.replaceChild(newSelect, elements.settingArchetype);
        elements.settingArchetype = newSelect;
        
        // Add event listener to show toast when user tries to change archetype
        elements.settingArchetype.addEventListener('change', function(e) {
            // Always revert to current archetype
            this.value = currentArchetype;
            
            // Show toast message
            window.showToast(
                'You can only use 1 persona in free tier. To use multiple personas, please upgrade your plan.',
                'warning',
                12000
            );
        });
    }
    
    if (elements.settingAttachment) {
        elements.settingAttachment.value = currentPersona.attachment_style || 'secure';
    }
    
    if (elements.settingFlirtiness) {
        elements.settingFlirtiness.value = currentPersona.flirtiness || 'subtle';
    }
    
    if (elements.settingToxicity) {
        elements.settingToxicity.value = currentPersona.toxicity || 'healthy';
    }
}

async function loadSectionData(sectionId) {
    showLoading();
    
    try {
        switch (sectionId) {
            case 'chat':
                await loadChatBots();  // Load bots first to populate dropdown
                await loadChatHistory();
                break;
            case 'my-bots':
                await loadMyBots();
                break;
            case 'settings':
                await loadSettings();
                // Load all bots for selector
                if (allUserBots.length === 0) {
                    const response = await api.bots.getAll();
                    allUserBots = response.bots || [];
                    
                    // Try to restore from localStorage first, then fall back to primary
                    const savedBotId = localStorage.getItem('selectedBotId');
                    if (savedBotId && allUserBots.some(b => b.id === savedBotId)) {
                        selectedBotId = savedBotId;
                        console.log('[loadSectionData] Restored settings bot from localStorage:', savedBotId);
                    } else {
                        selectedBotId = response.primary_bot_id || (allUserBots.length > 0 ? allUserBots[0].id : null);
                        console.log('[loadSectionData] Using primary or first bot:', selectedBotId);
                    }
                    
                    populateBotSelectors();
                    if (selectedBotId) {
                        await loadBotSettings(selectedBotId);
                    }
                } else {
                    // Bots already loaded, just restore selection and load settings
                    const savedBotId = localStorage.getItem('selectedBotId');
                    if (savedBotId && allUserBots.some(b => b.id === savedBotId)) {
                        selectedBotId = savedBotId;
                        console.log('[loadSectionData] Restored settings bot from localStorage (bots already loaded):', savedBotId);
                    } else if (!selectedBotId) {
                        selectedBotId = allUserBots.length > 0 ? allUserBots[0].id : null;
                    }
                    
                    populateBotSelectors();
                    if (selectedBotId) {
                        await loadBotSettings(selectedBotId);
                    }
                }
                break;
            case 'boundaries':
                await loadBoundaries();
                break;
            case 'analytics':
                await loadAnalytics();
                break;
            case 'memory':
                await loadMemory();
                break;
            case 'upgrade':
                // No API call needed for upgrade section
                break;
        }
    } catch (error) {
        console.error(`Error loading ${sectionId}:`, error);
        showError(`Failed to load ${sectionId} data.`);
    } finally {
        hideLoading();
    }
}

// Navigation
function navigateToSection(sectionId) {
    dashLog('[navigateToSection] Navigating to:', sectionId);
    
    // Close sidebar on mobile after navigation
    const sidebar = document.querySelector('.sidebar');
    const windowWidth = window.innerWidth;
    
    if (windowWidth <= 1024 && sidebar && !sidebar.classList.contains('collapsed')) {
        dashLog('[navigateToSection] Mobile detected - closing sidebar');
        sidebar.classList.add('collapsed');
        const icon = elements.sidebarToggle ? elements.sidebarToggle.querySelector('i') : null;
        if (icon) {
            icon.className = 'fas fa-bars';
        }
        // Remove backdrop
        if (elements.sidebarBackdrop) {
            elements.sidebarBackdrop.classList.remove('active');
        }
    }
    
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    const navItem = document.querySelector(`.nav-item[href="#${sectionId}"]`);
    if (navItem) {
        navItem.classList.add('active');
    }
    
    // Save to localStorage for persistence on page refresh
    localStorage.setItem('dashboardSection', sectionId);
    
    // Update page title
    const pageTitles = {
        'chat': 'Chat',
        'my-bots': 'My Bots',
        'settings': 'Settings',
        'boundaries': 'Boundaries',
        'analytics': 'Analytics',
        'memory': 'Memory',
        'upgrade': 'Upgrade'
    };
    
    const pageSubtitles = {
        'chat': 'Talk to your AI companion',
        'settings': 'Customize your companion',
        'boundaries': 'Set your comfort limits',
        'analytics': 'View your chat statistics',
        'memory': "See what your AI remembers",
        'upgrade': 'Unlock premium features'
    };
    
    if (elements.pageTitle) {
        elements.pageTitle.textContent = pageTitles[sectionId] || 'Dashboard';
    }
    
    if (elements.pageSubtitle) {
        elements.pageSubtitle.textContent = pageSubtitles[sectionId] || '';
    }
    
    // Show/hide sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(sectionId).classList.add('active');
    
    // Load section data
    loadSectionData(sectionId);
}

// Sidebar Functions
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const container = document.querySelector('.dashboard-container');
    const mobileToggle = document.getElementById('mobileMenuToggle');

    if (!sidebar) return;
    dashLog('[toggleSidebar] Current state:', sidebar.classList.contains('collapsed'));
    
    sidebar.classList.toggle('collapsed');
    
    // Handle backdrop on mobile
    if (elements.sidebarBackdrop) {
        if (sidebar.classList.contains('collapsed')) {
            elements.sidebarBackdrop.classList.remove('active');
        } else {
            elements.sidebarBackdrop.classList.add('active');
        }
    }
    
    // Update mobile menu toggle icon
    if (mobileToggle) {
        const mobileIcon = mobileToggle.querySelector('i');
        if (mobileIcon) {
            if (sidebar.classList.contains('collapsed')) {
                mobileIcon.className = 'fas fa-bars';
            } else {
                mobileIcon.className = 'fas fa-times';
            }
        }
    }
    
    const icon = elements.sidebarToggle ? elements.sidebarToggle.querySelector('i') : null;
    if (icon) {
        if (sidebar.classList.contains('collapsed')) {
            icon.className = 'fas fa-bars';
            dashLog('[toggleSidebar] Sidebar collapsed');
        } else {
            icon.className = 'fas fa-times';
            dashLog('[toggleSidebar] Sidebar expanded');
        }
    }
}

// Chat Functions
async function loadChatHistory() {
    try {
        // If no bot selected, load bots first
        if (!currentBotId) {
            await loadChatBots();
            if (!currentBotId) {
                showEmptyBotState();
                return;
            }
        }
        
        const data = await api.messages.getHistory(50, 0, null, currentBotId);
        
        if (!data || !data.messages) {
            throw new Error('Invalid response format');
        }
        
        displayChatMessages(data.messages);
        
    } catch (error) {
        console.error('Error loading chat history:', error);
        // Show empty chat state
        elements.chatMessages.innerHTML = `
            <div class="empty-chat">
                <i class="fas fa-comment-slash"></i>
                <h3>Start a conversation</h3>
                <p>Send a message to begin chatting with your AI companion</p>
                <button class="btn btn-primary" onclick="sendFirstMessage()">
                    <i class="fas fa-comment"></i>
                    Say Hello!
                </button>
            </div>
        `;
    }
}

async function loadChatBots() {
    try {
        console.log('[loadChatBots] Starting...');
        const chatBotSelect = document.getElementById('chatBotSelect');
        console.log('[loadChatBots] chatBotSelect element:', chatBotSelect);
        
        if (!chatBotSelect) {
            console.error('[loadChatBots] chatBotSelect element not found!');
            return;
        }
        
        // Always fetch fresh data for chat
        console.log('[loadChatBots] Fetching bots from API...');
        const response = await api.bots.getAll();
        console.log('[loadChatBots] API response:', response);
        
        allUserBots = response.bots || [];
        
        console.log('[loadChatBots] Loaded', allUserBots.length, 'bots:', allUserBots);
        
        // Clear and populate selector
        chatBotSelect.innerHTML = '';
        
        if (allUserBots.length === 0) {
            console.log('[loadChatBots] No bots found, showing empty state');
            chatBotSelect.innerHTML = '<option value="">No bots available - Create one!</option>';
            showEmptyBotState();
            return;
        }
        
        console.log('[loadChatBots] Populating dropdown with', allUserBots.length, 'bots');
        allUserBots.forEach((bot, index) => {
            console.log(`[loadChatBots] Adding bot ${index}:`, bot.bot_name, bot.id);
            const option = document.createElement('option');
            option.value = bot.id;
            option.textContent = `${bot.bot_name} (${formatArchetype(bot.archetype)})`;
            if (bot.is_primary) {
                option.selected = true;
                currentBotId = bot.id;
                console.log('[loadChatBots] Set primary bot:', bot.bot_name);
            }
            chatBotSelect.appendChild(option);
        });
        
        console.log('[loadChatBots] Dropdown options count:', chatBotSelect.options.length);
        
        // Try to restore previously selected bot from localStorage
        const savedBotId = localStorage.getItem('selectedBotId');
        console.log('[loadChatBots] Saved bot ID from localStorage:', savedBotId);
        
        if (savedBotId && allUserBots.some(b => b.id === savedBotId)) {
            currentBotId = savedBotId;
            chatBotSelect.value = savedBotId;
            console.log('[loadChatBots] Restored bot from localStorage:', savedBotId);
        }
        // If no primary bot and no saved bot, select first one
        else if (!currentBotId && allUserBots.length > 0) {
            currentBotId = allUserBots[0].id;
            chatBotSelect.value = currentBotId;
            console.log('[loadChatBots] No primary bot, selected first:', allUserBots[0].bot_name);
        }
        
        // Update chat header with selected bot
        if (currentBotId) {
            console.log('[loadChatBots] Updating chat header for bot:', currentBotId);
            await updateChatHeader(currentBotId);
        }
        
        console.log('[loadChatBots] Completed successfully');
        
    } catch (error) {
        console.error('[loadChatBots] Error:', error);
        console.error('[loadChatBots] Error stack:', error.stack);
    }
}

async function switchChatBot(botId) {
    try {
        showLoading();
        currentBotId = botId;
        
        // Save selected bot to localStorage for persistence
        localStorage.setItem('selectedBotId', botId);
        console.log('[switchChatBot] Saved bot ID to localStorage:', botId);
        
        // Update chat header
        await updateChatHeader(botId);
        
        // Reload chat history for this bot
        await loadChatHistory();
        
    } catch (error) {
        console.error('Error switching chat bot:', error);
        showError('Failed to switch bot');
    } finally {
        hideLoading();
    }
}

async function updateChatHeader(botId) {
    const bot = allUserBots.find(b => b.id === botId);
    if (!bot) return;
    
    const companionName = document.getElementById('companionName');
    const companionArchetype = document.getElementById('companionArchetype');
    const companionAvatar = document.getElementById('companionAvatar');
    
    if (companionName) {
        companionName.textContent = bot.bot_name || 'AI Companion';
    }
    
    if (companionArchetype) {
        companionArchetype.textContent = formatArchetype(bot.archetype);
    }
    
    if (companionAvatar) {
        const avatarIcons = {
            golden_retriever: 'fas fa-dog',
            tsundere: 'fas fa-sun',
            lawyer: 'fas fa-gavel',
            cool_girl: 'fas fa-sunglasses',
            toxic_ex: 'fas fa-fire'
        };
        companionAvatar.innerHTML = `<i class="${avatarIcons[bot.archetype] || 'fas fa-robot'}"></i>`;
    }
}

function formatArchetype(archetype) {
    const names = {
        golden_retriever: 'Golden Retriever',
        tsundere: 'Tsundere',
        lawyer: 'Lawyer',
        cool_girl: 'Cool Girl',
        toxic_ex: 'Toxic Ex'
    };
    return names[archetype] || archetype;
}

function showEmptyBotState() {
    if (elements.chatMessages) {
        elements.chatMessages.innerHTML = `
            <div class="empty-chat">
                <i class="fas fa-robot"></i>
                <h3>No AI Companions Yet</h3>
                <p>Create your first AI companion through the onboarding quiz</p>
                <button class="btn btn-primary" onclick="window.location.href='quiz.html'">
                    <i class="fas fa-plus"></i>
                    Create Companion
                </button>
            </div>
        `;
    }
}

function displayChatMessages(messages) {
    if (!messages || messages.length === 0) {
        elements.chatMessages.innerHTML = `
            <div class="empty-chat">
                <i class="fas fa-comment-slash"></i>
                <h3>Start a conversation</h3>
                <p>Send a message to begin chatting with your AI companion</p>
                <button class="btn btn-primary" onclick="sendFirstMessage()">
                    <i class="fas fa-comment"></i>
                    Say Hello!
                </button>
            </div>
        `;
        return;
    }
    
    elements.chatMessages.innerHTML = '';
    messages.forEach(message => {
        const messageElement = createMessageElement(message);
        elements.chatMessages.appendChild(messageElement);
    });
    
    // Scroll to bottom
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function createMessageElement(message) {
    const div = document.createElement('div');
    div.className = `message ${message.role}`;
    
    const time = new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    div.innerHTML = `
        <div class="message-content">${escapeHtml(message.content)}</div>
        <div class="message-time">${time}</div>
    `;
    
    return div;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateCharCount() {
    const count = elements.messageInput.value.length;
    if (elements.charCount) {
        elements.charCount.textContent = `${count}/4000`;
        
        // Update color based on count
        if (count > 3500) {
            elements.charCount.style.color = '#ef4444';
        } else if (count > 3000) {
            elements.charCount.style.color = '#f59e0b';
        } else {
            elements.charCount.style.color = '';
        }
    }
}

function handleMessageKeypress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message) return;
    
    // Check daily limit
    if (currentUser && currentUser.limits && currentUser.limits.messages_today >= currentUser.limits.daily_message_limit) {
        showError('Daily message limit reached. Upgrade for more messages.');
        return;
    }
    
    // Add user message to chat
    const userMessage = {
        role: 'user',
        content: message,
        created_at: new Date().toISOString()
    };
    
    elements.chatMessages.appendChild(createMessageElement(userMessage));
    elements.messageInput.value = '';
    updateCharCount();
    
    // Scroll to bottom
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    
    // Show typing indicator
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'message bot typing';
    typingIndicator.innerHTML = `
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    elements.chatMessages.appendChild(typingIndicator);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    
    try {
        // Send message using API module
        dashLog('📤 Sending message with bot_id:', currentBotId, 'type:', typeof currentBotId);
        console.log('[sendMessage] Current bot_id:', currentBotId, 'All bots:', allUserBots);
        
        const data = await api.messages.send(message, currentBotId);
        
        dashLog('✅ Message sent:', data);
        
        // Remove typing indicator
        typingIndicator.remove();
        
        // Add bot response if available
        if (data.reply || data.response) {
            const botMessage = {
                role: 'bot',
                content: data.reply || data.response || 'Message received',
                created_at: new Date().toISOString()
            };
            
            elements.chatMessages.appendChild(createMessageElement(botMessage));
        }
        
        // Update message count
        if (currentUser.limits) {
            currentUser.limits.messages_today = (currentUser.limits.messages_today || 0) + 1;
            updateUserUI();
        }
        
        // Scroll to bottom
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
        
    } catch (error) {
        console.error('❌ Error sending message:', error);
        typingIndicator.remove();
        
        // Provide specific error messages based on error status
        let errorMessage = 'Failed to send message. Please try again.';
        if (error.status === 404) {
            errorMessage = 'Bot not found. Please select a valid bot.';
        } else if (error.status === 400) {
            errorMessage = 'Invalid bot ID. Please refresh and try again.';
        } else if (error.status >= 500) {
            errorMessage = 'Server error. Please try again in a moment.';
        }
        
        showError(errorMessage);
    }
}

function sendFirstMessage() {
    elements.messageInput.value = 'Hello!';
    sendMessage();
}

async function clearChat() {
    if (!confirm('Are you sure you want to clear the chat history? This cannot be undone.')) {
        return;
    }

    try {
        showLoading('Clearing chat history...');
        const userId = currentUser?.id || currentUser?.user_id || null;
        const botId = currentBotId || null;
        
        dashLog('[clearChat] Clearing history for bot:', botId, 'user:', userId);
        
        await api.messages.clearHistory(userId, botId);

        dashLog('[clearChat] History cleared successfully');
        
        elements.chatMessages.innerHTML = `
            <div class="empty-chat">
                <i class="fas fa-comment-slash"></i>
                <h3>Start a conversation</h3>
                <p>Send a message to begin chatting with your AI companion</p>
                <button class="btn btn-primary" onclick="sendFirstMessage()">
                    <i class="fas fa-comment"></i>
                    Say Hello!
                </button>
            </div>
        `;
        
        showSuccess('Chat history cleared successfully!');
    } catch (error) {
        console.error('❌ Error clearing chat history:', error);
        
        // Check if error is a timeout - the operation may still have succeeded
        if (error.status === 408 || error.name === 'AbortError') {
            showSuccess('Chat history cleared! (Confirming...)', 'info');
            // Reload the chat to verify
            setTimeout(() => loadChatHistory(), 2000);
        } else {
            showError(`Failed to clear chat history: ${error.message || 'Unknown error'}. Please try again.`);
        }
    } finally {
        hideLoading();
    }
}

function refreshChat() {
    dashLog('[refreshChat] Refreshing current section data');
    const activeSection = document.querySelector('.content-section.active');
    if (activeSection) {
        const sectionId = activeSection.id;
        dashLog('[refreshChat] Active section:', sectionId);
        
        // For settings page, preserve the selected bot
        if (sectionId === 'settings') {
            // Save current selection before refresh
            const savedBotId = localStorage.getItem('selectedBotId');
            loadSectionData(sectionId).then(() => {
                // Restore selection after load
                if (savedBotId) {
                    selectedBotId = savedBotId;
                    if (allUserBots.length > 0 && allUserBots.some(b => b.id === savedBotId)) {
                        loadBotSettings(savedBotId);
                    }
                }
            });
        } else {
            loadSectionData(sectionId);
        }
    } else {
        dashLog('[refreshChat] No active section, loading chat');
        loadChatHistory();
    }
}

function startNewChat() {
    if (elements.chatMessages.querySelector('.message')) {
        if (confirm('Start a new chat? Your current chat will be saved.')) {
            clearChat();
        }
    }
}

// Settings Functions
async function loadSettings() {
    try {
        // Load advanced settings
        if (elements.advancedSettings && currentPersona && currentPersona.advanced_settings) {
            const advancedSettings = currentPersona.advanced_settings;
            elements.advancedSettings.innerHTML = '';
            
            for (const [key, value] of Object.entries(advancedSettings)) {
                const settingDiv = document.createElement('div');
                settingDiv.className = 'advanced-setting';
                
                const label = document.createElement('label');
                label.textContent = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                
                const select = document.createElement('select');
                select.id = `advanced_${key}`;
                
                // Add options based on setting type
                const options = getSettingOptions(key);
                options.forEach(option => {
                    const optionElement = document.createElement('option');
                    optionElement.value = option;
                    optionElement.textContent = option.charAt(0).toUpperCase() + option.slice(1);
                    if (option === value) {
                        optionElement.selected = true;
                    }
                    select.appendChild(optionElement);
                });
                
                settingDiv.appendChild(label);
                settingDiv.appendChild(select);
                elements.advancedSettings.appendChild(settingDiv);
            }
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

function getSettingOptions(settingKey) {
    const options = {
        temperament: ['warm', 'cool', 'hot', 'chaotic'],
        humor_type: ['dry', 'silly', 'dark', 'witty'],
        confidence: ['cocky', 'confident', 'humble', 'fluctuating'],
        power_dynamic: ['they_dominate', 'you_dominate', 'equal', 'brat', 'switches'],
        affection_style: ['words', 'acts', 'presence', 'quality_time', 'withholding'],
        emoji_usage: ['none', 'minimal', 'moderate', 'heavy'],
        message_length: ['short', 'medium', 'long', 'chaotic'],
        typing_style: ['proper', 'casual', 'lowercase', 'chaotic'],
        clinginess: ['independent', 'balanced', 'clingy', 'hot_cold'],
        jealousy_level: ['none', 'subtle', 'moderate', 'spicy'],
        roast_intensity: ['off', 'gentle', 'medium'],
        sass_level: ['none', 'low', 'medium', 'high']
    };
    
    return options[settingKey] || [];
}

async function saveSettings() {
    // Use the new saveBotSettings function
    await saveBotSettings();
}

async function saveSettingsOld() {
    showLoading();
    
    try {
        // Force archetype to remain unchanged for free tier users
        const currentArchetype = currentPersona.archetype || 'golden_retriever';
        
        const settings = {
            bot_name: elements.settingBotName.value,
            bot_gender: elements.settingGender.value,
            archetype: currentArchetype,  // Always use current archetype, ignore user selection
            attachment_style: elements.settingAttachment.value,
            flirtiness: elements.settingFlirtiness.value,
            toxicity: elements.settingToxicity.value,
            advanced_settings: {}
        };
        
        // Collect advanced settings
        const advancedSettings = elements.advancedSettings.querySelectorAll('.advanced-setting');
        advancedSettings.forEach(setting => {
            const select = setting.querySelector('select');
            const key = select.id.replace('advanced_', '');
            settings.advanced_settings[key] = select.value;
        });
        
        // Update via API
        const response = await api.settings.update(settings);
        
        // Update local data
        currentPersona = { ...currentPersona, ...settings };
        localStorage.setItem('aiCompanionData', JSON.stringify(currentPersona));
        
        // Update UI
        updatePersonaUI();
        
        showSuccess('Settings saved successfully!');
        
    } catch (error) {
        console.error('Error saving settings:', error);
        showError('Failed to save settings. Please try again.');
    } finally {
        hideLoading();
    }
}

function renderAdvancedSettings(advancedSettings) {
    if (!elements.advancedSettings) return;
    
    const settings = advancedSettings || {};
    
    // Define all available advanced settings options
    const advancedSettingsConfig = {
        temperament: {
            label: 'Temperament',
            options: ['warm', 'cool', 'hot']
        },
        humor_type: {
            label: 'Humor Type',
            options: ['silly', 'dry', 'witty', 'dark']
        },
        confidence: {
            label: 'Confidence',
            options: ['humble', 'confident', 'cocky', 'fluctuating']
        },
        power_dynamic: {
            label: 'Power Dynamic',
            options: ['you_dominate', 'they_dominate', 'brat', 'switches']
        },
        affection_style: {
            label: 'Affection Style',
            options: ['words', 'acts', 'quality_time', 'presence', 'withholding']
        },
        emoji_usage: {
            label: 'Emoji Usage',
            options: ['none', 'minimal', 'moderate', 'heavy']
        },
        message_length: {
            label: 'Message Length',
            options: ['short', 'medium', 'long', 'chaotic']
        },
        typing_style: {
            label: 'Typing Style',
            options: ['lowercase', 'proper', 'casual', 'chaotic']
        },
        clinginess: {
            label: 'Clinginess Level',
            options: ['independent', 'clingy', 'hot_cold']
        }
    };
    
    // Clear existing content
    elements.advancedSettings.innerHTML = '';
    
    // Create setting elements
    Object.entries(advancedSettingsConfig).forEach(([key, config]) => {
        const settingDiv = document.createElement('div');
        settingDiv.className = 'setting-item advanced-setting';
        
        const label = document.createElement('label');
        label.textContent = config.label;
        
        const select = document.createElement('select');
        select.id = `advanced_${key}`;
        select.className = 'form-control';
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select...';
        select.appendChild(defaultOption);
        
        // Add available options
        config.options.forEach(optionValue => {
            const option = document.createElement('option');
            option.value = optionValue;
            option.textContent = optionValue.charAt(0).toUpperCase() + optionValue.slice(1).replace(/_/g, ' ');
            
            // Set selected if it matches the current value
            if (settings[key] === optionValue) {
                option.selected = true;
            }
            select.appendChild(option);
        });
        
        settingDiv.appendChild(label);
        settingDiv.appendChild(select);
        elements.advancedSettings.appendChild(settingDiv);
    });
}

function resetAdvancedSettings() {
    if (confirm('Reset all advanced settings to defaults?')) {
        // Get default settings based on archetype
        const archetypeDefaults = {
            golden_retriever: {
                temperament: 'warm',
                humor_type: 'silly',
                confidence: 'humble',
                power_dynamic: 'you_dominate',
                affection_style: 'words',
                emoji_usage: 'heavy',
                message_length: 'medium',
                typing_style: 'casual',
                clinginess: 'clingy'
            },
            tsundere: {
                temperament: 'cool',
                humor_type: 'dry',
                confidence: 'fluctuating',
                power_dynamic: 'brat',
                affection_style: 'acts',
                emoji_usage: 'minimal',
                message_length: 'short',
                typing_style: 'lowercase',
                clinginess: 'independent'
            },
            lawyer: {
                temperament: 'cool',
                humor_type: 'dry',
                confidence: 'cocky',
                power_dynamic: 'they_dominate',
                affection_style: 'quality_time',
                emoji_usage: 'none',
                message_length: 'medium',
                typing_style: 'proper',
                clinginess: 'independent'
            },
            cool_girl: {
                temperament: 'cool',
                humor_type: 'witty',
                confidence: 'confident',
                power_dynamic: 'they_dominate',
                affection_style: 'presence',
                emoji_usage: 'minimal',
                message_length: 'short',
                typing_style: 'lowercase',
                clinginess: 'independent'
            },
            toxic_ex: {
                temperament: 'hot',
                humor_type: 'dark',
                confidence: 'fluctuating',
                power_dynamic: 'switches',
                affection_style: 'withholding',
                emoji_usage: 'moderate',
                message_length: 'chaotic',
                typing_style: 'chaotic',
                clinginess: 'hot_cold'
            }
        };
        
        const archetype = (currentPersona && currentPersona.archetype) ? currentPersona.archetype : 'golden_retriever';
        const defaults = archetypeDefaults[archetype] || archetypeDefaults.golden_retriever;
        
        // Update UI
        const advancedSettings = elements.advancedSettings.querySelectorAll('.advanced-setting');
        advancedSettings.forEach(setting => {
            const select = setting.querySelector('select');
            const key = select.id.replace('advanced_', '');
            if (defaults[key]) {
                select.value = defaults[key];
            }
        });
        
        showSuccess('Advanced settings reset to defaults.');
    }
}

// Boundaries Functions
async function loadBoundaries() {
    try {
        const response = await api.boundaries.get();
        displayBoundaries(response);
    } catch (error) {
        console.error('Error loading boundaries:', error);
        elements.boundariesList.innerHTML = '<p class="text-muted">Failed to load boundaries. Please try again.</p>';
    }
}

function displayBoundaries(boundaries) {
    if (!boundaries || boundaries.length === 0) {
        elements.boundariesList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-shield-alt"></i>
                <h4>No boundaries set</h4>
                <p>Add your first boundary below</p>
            </div>
        `;
        return;
    }
    
    elements.boundariesList.innerHTML = '';
    boundaries.forEach(boundary => {
        // Map API response to expected format
        const mappedBoundary = {
            id: boundary.id,
            type: boundary.boundary_type,
            value: boundary.boundary_value,
            active: boundary.active
        };
        const boundaryElement = createBoundaryElement(mappedBoundary);
        elements.boundariesList.appendChild(boundaryElement);
    });
}

function createBoundaryElement(boundary) {
    // Validate boundary object - accept both formats from API
    if (!boundary || !boundary.id) {
        dashLog('Invalid boundary object:', boundary);
        return null;
    }
    
    // Handle both API response formats: boundary_type/boundary_value OR type/value
    const boundaryType = boundary.boundary_type || boundary.type;
    const boundaryValue = boundary.boundary_value || boundary.value;
    
    if (!boundaryType || !boundaryValue) {
        dashLog('Invalid boundary object - missing type or value:', boundary);
        return null;
    }
    
    const div = document.createElement('div');
    div.className = 'boundary-item';
    div.dataset.id = boundary.id;
    
    const typeClass = `boundary-type ${boundaryType}`;
    const typeLabel = boundaryType.charAt(0).toUpperCase() + boundaryType.slice(1);
    
    div.innerHTML = `
        <div class="boundary-info">
            <span class="${typeClass}">${typeLabel}</span>
            <div class="boundary-details">
                <h4>${boundaryValue}</h4>
            </div>
        </div>
        <div class="boundary-actions">
            <button class="btn-icon toggle-boundary ${boundary.active ? 'active' : ''}" title="${boundary.active ? 'Active' : 'Inactive'}">
                <i class="fas ${boundary.active ? 'fa-toggle-on' : 'fa-toggle-off'}"></i>
            </button>
            <button class="btn-icon btn-danger delete-boundary" title="Delete">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    
    return div;
}

function updateBoundaryHint() {
    const type = elements.boundaryType.value;
    const hints = {
        topic: 'For topic: "work", "politics", "family", etc.',
        timing: 'For timing: "no morning messages", "no late night texts", etc.',
        behavior: 'For behavior: "no flirting", "no questions about work", etc.',
        frequency: 'For frequency: "max 3 messages per hour", "only message if I initiate", etc.'
    };
    
    if (elements.boundaryHint) {
        elements.boundaryHint.textContent = hints[type] || '';
    }
}

async function addBoundary() {
    dashLog('[addBoundary] Starting... boundaryType element:', elements.boundaryType);
    dashLog('[addBoundary] boundaryValue element:', elements.boundaryValue);
    
    const type = elements.boundaryType ? elements.boundaryType.value : null;
    const value = elements.boundaryValue ? elements.boundaryValue.value.trim() : null;
    
    dashLog('[addBoundary] type:', type, 'value:', value);
    
    if (!type || !value) {
        dashLog('[addBoundary] Missing type or value - type:', type, 'value:', value);
        showError('Please enter a boundary type and value');
        return;
    }
    
    try {
        dashLog('[addBoundary] Calling API with:', { boundary_type: type, boundary_value: value, active: true });
        const newBoundary = await api.boundaries.create({
            boundary_type: type,
            boundary_value: value,
            active: true
        });
        
        dashLog('[addBoundary] API Response:', newBoundary);
        
        // Only add if we got a valid boundary back
        if (!newBoundary) {
            dashLog('[addBoundary] No boundary returned from API');
            showError('Failed to create boundary - no response from server');
            return;
        }
        
        if (!newBoundary.id) {
            dashLog('[addBoundary] Boundary missing ID:', newBoundary);
            showError('Failed to create boundary - invalid response structure');
            return;
        }
        
        const boundaryElement = createBoundaryElement(newBoundary);
        if (boundaryElement) {
            // Check if we need to clear the empty state first
            const emptyState = elements.boundariesList.querySelector('.empty-state');
            if (emptyState) {
                emptyState.remove();
            }
            
            // Check if boundary already exists in DOM to prevent duplicates
            const existingBoundary = elements.boundariesList.querySelector(`[data-id="${newBoundary.id}"]`);
            if (existingBoundary) {
                dashLog('[addBoundary] Boundary already exists in DOM, not adding duplicate');
                return;
            }
            
            elements.boundariesList.appendChild(boundaryElement);
            
            // Clear form
            if (elements.boundaryValue) {
                elements.boundaryValue.value = '';
            }
            showSuccess('Boundary added successfully!');
        } else {
            console.error('[addBoundary] Failed to create boundary element');
        }
    } catch (error) {
        console.error('[addBoundary] Error:', error);
        // Handle specific error messages from API
        const message = (error.data && error.data.message) ? error.data.message : (error.message || 'Failed to add boundary');
        showError(message);
    }
}

async function toggleBoundary(id) {
    try {
        const boundaryItem = elements.boundariesList.querySelector(`[data-id="${id}"]`);
        if (!boundaryItem) return;
        
        const toggleBtn = boundaryItem.querySelector('.boundary-actions .btn-icon:first-child');
        const icon = toggleBtn.querySelector('i');
        const currentActive = toggleBtn.classList.contains('active');
        const newActive = !currentActive;
        
        // Extract the boundary type and value from DOM
        const boundaryInfo = boundaryItem.querySelector('.boundary-info');
        const typeSpan = boundaryInfo.querySelector('.boundary-type');
        const detailsH4 = boundaryInfo.querySelector('.boundary-details h4');
        
        const boundaryType = typeSpan.className.replace('boundary-type ', '').toLowerCase();
        const boundaryValue = detailsH4.textContent;
        
        // Call API to update boundary with full boundary object
        await api.boundaries.update(id, {
            boundary_type: boundaryType,
            boundary_value: boundaryValue,
            active: newActive
        });
        
        // Update UI
        if (newActive) {
            toggleBtn.classList.add('active');
            icon.className = 'fas fa-toggle-on';
            toggleBtn.setAttribute('title', 'Active');
            showSuccess('Boundary activated');
        } else {
            toggleBtn.classList.remove('active');
            icon.className = 'fas fa-toggle-off';
            toggleBtn.setAttribute('title', 'Inactive');
            showSuccess('Boundary deactivated');
        }
    } catch (error) {
        console.error('Error toggling boundary:', error);
        showError('Failed to update boundary');
    }
}

async function deleteBoundary(id) {
    if (confirm('Are you sure you want to delete this boundary?')) {
        try {
            dashLog('[deleteBoundary] Deleting boundary:', id);
            await api.boundaries.delete(id);
            dashLog('[deleteBoundary] API call successful');
            
            const boundaryItem = elements.boundariesList.querySelector(`[data-id="${id}"]`);
            if (boundaryItem) {
                dashLog('[deleteBoundary] Removing boundary from DOM');
                boundaryItem.remove();
                
                // Check if list is now empty
                if (elements.boundariesList.children.length === 0) {
                    elements.boundariesList.innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-shield-alt"></i>
                            <h4>No boundaries set</h4>
                            <p>Add your first boundary below</p>
                        </div>
                    `;
                }
            }
            
            showSuccess('Boundary deleted');
        } catch (error) {
            console.error('[deleteBoundary] Error:', error);
            showError((error.data && error.data.message) ? error.data.message : 'Failed to delete boundary');
        }
    }
}

// Analytics Functions
async function loadAnalytics() {
    try {
        const data = await api.analytics.getStats();
        
        dashLog('📊 Analytics data received:', data);
        
        // Update stats
        if (elements.totalMessages) elements.totalMessages.textContent = data.total_messages || '0';
        if (elements.activeDays) elements.activeDays.textContent = data.active_days || '0';
        if (elements.avgLength) elements.avgLength.textContent = data.avg_message_length || '0';
        if (elements.commonMood) {
            const mood = data.common_mood || 'neutral';
            elements.commonMood.textContent = mood.charAt(0).toUpperCase() + mood.slice(1);
        }
        
        // Draw charts with real data
        drawMessagesChart(data);
        drawMoodChart(data);
        loadRecentActivity();
    } catch (error) {
        console.error('❌ Error loading analytics:', error);
        showError('Failed to load analytics data.');
        // Show zero state when data fails to load
        if (elements.totalMessages) elements.totalMessages.textContent = '0';
        if (elements.activeDays) elements.activeDays.textContent = '0';
        if (elements.avgLength) elements.avgLength.textContent = '0';
        if (elements.commonMood) elements.commonMood.textContent = 'No Data';
    }
}

function drawMessagesChart(analyticsData) {
    if (!elements.messagesChart) return;
    
    // Get the last 7 days labels
    const days = [];
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        days.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
    }
    
    // Use real data from backend
    const data = (analyticsData && analyticsData.messages_per_day && analyticsData.messages_per_day.length === 7) 
        ? analyticsData.messages_per_day 
        : [0, 0, 0, 0, 0, 0, 0];
    
    const maxValue = Math.max(...data, 1);
    
    elements.messagesChart.innerHTML = '';
    
    data.forEach((value, index) => {
        const height = maxValue > 0 ? (value / maxValue) * 150 : 0;
        const bar = document.createElement('div');
        bar.className = 'chart-bar';
        bar.style.height = `${height}px`;
        bar.title = `${value} messages on ${days[index]}`;
        
        const label = document.createElement('div');
        label.className = 'chart-bar-label';
        label.textContent = days[index];
        
        bar.appendChild(label);
        elements.messagesChart.appendChild(bar);
    });
}

function drawMoodChart(analyticsData) {
    if (!elements.moodChart) return;
    
    // Mood colors mapping
    const moodColors = {
        happy: '#10b981',
        neutral: '#6366f1',
        sad: '#8b5cf6',
        excited: '#ec4899',
        anxious: '#f59e0b',
        angry: '#ef4444',
        calm: '#3b82f6',
        default: '#6b7280'
    };
    
    let moods = [];
    
    if (analyticsData && analyticsData.mood_distribution && Object.keys(analyticsData.mood_distribution).length > 0) {
        // Calculate total for percentage
        const total = Object.values(analyticsData.mood_distribution).reduce((sum, val) => sum + val, 0);
        
        moods = Object.entries(analyticsData.mood_distribution)
            .map(([name, count]) => ({
                name: name.charAt(0).toUpperCase() + name.slice(1),
                value: count,
                percentage: total > 0 ? Math.round((count / total) * 100) : 0,
                color: moodColors[name.toLowerCase()] || moodColors.default
            }))
            .sort((a, b) => b.value - a.value); // Sort by count descending
    }
    
    elements.moodChart.innerHTML = '';
    
    if (moods.length === 0) {
        elements.moodChart.innerHTML = '<div class="empty-state"><p>No mood data available yet</p></div>';
        return;
    }
    
    const maxValue = Math.max(...moods.map(m => m.value), 1);
    
    moods.forEach(mood => {
        const height = (mood.value / maxValue) * 150;
        const bar = document.createElement('div');
        bar.className = 'chart-bar';
        bar.style.height = `${height}px`;
        bar.style.backgroundColor = mood.color;
        bar.title = `${mood.name}: ${mood.value} messages (${mood.percentage}%)`;
        
        const label = document.createElement('div');
        label.className = 'chart-bar-label';
        label.textContent = mood.name;
        
        bar.appendChild(label);
        elements.moodChart.appendChild(bar);
    });
}

function loadRecentActivity() {
    if (!elements.activityList) return;
    
    // Example activity data
    const activities = [
        { type: 'message', title: 'Chat started', description: 'You started a new chat', time: '10 min ago' },
        { type: 'settings', title: 'Settings updated', description: 'Changed companion name', time: '2 hours ago' },
        { type: 'boundary', title: 'Boundary added', description: 'Added "no morning messages"', time: '1 day ago' },
        { type: 'proactive', title: 'Proactive message', description: 'Your companion sent a morning greeting', time: '2 days ago' }
    ];
    
    elements.activityList.innerHTML = '';
    
    activities.forEach(activity => {
        const activityElement = createActivityElement(activity);
        elements.activityList.appendChild(activityElement);
    });
}

function createActivityElement(activity) {
    const icons = {
        message: 'fas fa-comment',
        settings: 'fas fa-cog',
        boundary: 'fas fa-shield-alt',
        proactive: 'fas fa-bell'
    };
    
    const div = document.createElement('div');
    div.className = 'activity-item';
    
    div.innerHTML = `
        <div class="activity-icon">
            <i class="${icons[activity.type] || 'fas fa-circle'}"></i>
        </div>
        <div class="activity-details">
            <h4>${activity.title}</h4>
            <p>${activity.description}</p>
        </div>
        <div class="activity-time">${activity.time}</div>
    `;
    
    return div;
}

// Memory Functions
async function loadMemory() {
    try {
        const data = await api.memory.getSummary();
        
        dashLog('🧠 Memory data received:', data);
        
        // Update stats with real data
        if (elements.memoryCount) elements.memoryCount.textContent = data.total_memories || '0';
        if (elements.memoryCategories) {
            const categoryCount = data.categories ? data.categories.length : 0;
            elements.memoryCategories.textContent = categoryCount;
        }
        if (elements.memoryImportance) {
            elements.memoryImportance.textContent = (data.avg_importance || 0).toFixed(1);
        }
        
        // Load categories and memories with real data
        loadMemoryCategories(data.recent_memories || [], data.category_counts || {});
        loadMemories(data.recent_memories || []);
    } catch (error) {
        console.error('❌ Error loading memory:', error);
        showError('Failed to load memory data.');
        // Show zero state when data fails to load
        if (elements.memoryCount) elements.memoryCount.textContent = '0';
        if (elements.memoryCategories) elements.memoryCategories.textContent = '0';
        if (elements.memoryImportance) elements.memoryImportance.textContent = '0.0';
    }
}

function loadMemoryCategories(memories, categoryCounts = {}) {
    if (!elements.categoryTabs) return;
    
    // Use real category counts from backend
    const totalCount = memories.length;
    const categories = [
        { id: 'all', name: 'All', count: totalCount },
        { id: 'conversation', name: 'Conversation', count: categoryCounts.conversation || 0 },
        { id: 'personal', name: 'Personal', count: categoryCounts.personal || 0 },
        { id: 'preferences', name: 'Preferences', count: categoryCounts.preferences || 0 },
        { id: 'interests', name: 'Interests', count: categoryCounts.interests || 0 },
        { id: 'facts', name: 'Facts', count: categoryCounts.facts || 0 }
    ];
    
    elements.categoryTabs.innerHTML = '';
    
    categories.forEach(category => {
        const tab = document.createElement('div');
        tab.className = 'category-tab';
        if (category.id === 'all') tab.classList.add('active');
        tab.dataset.category = category.id;
        tab.textContent = `${category.name} (${category.count})`;
        tab.addEventListener('click', () => filterMemories(category.id, memories));
        elements.categoryTabs.appendChild(tab);
    });
}

function loadMemories(memories) {
    if (!elements.memoriesList) return;
    
    // Use real backend data with proper structure
    displayMemories(memories.map((mem) => ({
        id: mem.id || Math.random().toString(36),
        category: mem.category || 'conversation',
        content: mem.content,
        importance: mem.importance || 3,
        timestamp: mem.timestamp
    })));
}

function displayMemories(memories) {
    if (!memories || memories.length === 0) {
        elements.memoriesList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-brain"></i>
                <h4>No memories yet</h4>
                <p>Your AI companion will learn about you as you chat</p>
            </div>
        `;
        return;
    }
    
    elements.memoriesList.innerHTML = '';
    memories.forEach(memory => {
        const memoryElement = createMemoryElement(memory);
        elements.memoriesList.appendChild(memoryElement);
    });
}

function createMemoryElement(memory) {
    const div = document.createElement('div');
    div.className = `memory-item ${memory.category || 'conversation'}`;
    
    // Create star rating
    let stars = '';
    const importance = memory.importance || 3;
    for (let i = 1; i <= 5; i++) {
        stars += `<i class="fas fa-star${i <= importance ? '' : '-o'}"></i>`;
    }
    
    // Format timestamp if available
    let timeDisplay = '';
    if (memory.timestamp) {
        try {
            const date = new Date(memory.timestamp);
            timeDisplay = `<div class="memory-time">${date.toLocaleDateString()}</div>`;
        } catch (e) {
            // Invalid timestamp, skip
        }
    }
    
    const categoryName = memory.category ? memory.category.charAt(0).toUpperCase() + memory.category.slice(1) : 'Memory';
    
    div.innerHTML = `
        <span class="memory-category">${categoryName}</span>
        <p class="memory-content">${escapeHtml(memory.content)}</p>
        <div class="memory-importance">
            <span class="importance-stars">${stars}</span>
            <span class="importance-label">Importance: ${importance}/5</span>
        </div>
        ${timeDisplay}
    `;
    
    return div;
}

function filterMemories(category, allMemories = []) {
    // Update active tab
    if (elements.categoryTabs) {
        elements.categoryTabs.querySelectorAll('.category-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        const activeTab = elements.categoryTabs.querySelector(`[data-category="${category}"]`);
        if (activeTab) activeTab.classList.add('active');
    }
    
    // Filter memories by category
    let filteredMemories = allMemories;
    
    if (category !== 'all') {
        filteredMemories = allMemories.filter(mem => mem.category === category);
    }
    
    // Display filtered memories
    displayMemories(filteredMemories.map((mem) => ({
        id: mem.id || Math.random().toString(36),
        category: mem.category || 'conversation',
        content: mem.content,
        importance: mem.importance || 3,
        timestamp: mem.timestamp
    })));
}

async function refreshMemory() {
    try {
        await loadMemory();
        showSuccess('Memory refreshed successfully!');
    } catch (error) {
        console.error('❌ Error refreshing memory:', error);
        showError('Failed to refresh memory.');
    }
}

async function clearMemory() {
    if (confirm('Are you sure you want to clear all memory? This cannot be undone.')) {
        try {
            const userId = currentUser?.id || currentUser?.user_id || null;
            await api.memory.clear(userId);
            
            showSuccess('All memory cleared successfully!');
            // Clear UI
            if (elements.memoryCount) elements.memoryCount.textContent = '0';
            if (elements.memoryCategories) elements.memoryCategories.textContent = '0';
            if (elements.memoryImportance) elements.memoryImportance.textContent = '0.0';
            if (elements.memoriesList) {
                elements.memoriesList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-brain"></i>
                        <h4>Memory cleared</h4>
                        <p>Your AI companion will start learning anew</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('❌ Error clearing memory:', error);
            showError('Failed to clear memory.');
        }
    }
}

// Upgrade Functions
function upgradeTo(plan) {
    if (plan === 'plus' || plan === 'premium') {
        // In a real implementation, this would redirect to payment
        showInfo(`Redirecting to ${plan} plan checkout...`);
        
        // Mock payment flow
        setTimeout(() => {
            if (confirm(`Upgrade to ${plan} plan? This is a demo - in production this would process payment.`)) {
                currentUser.tier = plan;
                updateUserUI();
                showSuccess(`Successfully upgraded to ${plan} plan!`);
            }
        }, 500);
    }
}

// Support Functions
function showSupport() {
    elements.supportModal.classList.add('active');
}

function closeSupportModal() {
    elements.supportModal.classList.remove('active');
}

function sendSupportMessage() {
    showLoading();
    
    // Mock sending support message
    setTimeout(() => {
        hideLoading();
        closeSupportModal();
        showSuccess('Support message sent successfully. We\'ll get back to you soon.');
    }, 1500);
}

// Utility Functions
function showLoading() {
    if (elements.loadingOverlay) {
        elements.loadingOverlay.classList.add('active');
    }
}

function hideLoading() {
    if (elements.loadingOverlay) {
        elements.loadingOverlay.classList.remove('active');
    }
}

function showError(message) {
    if (typeof window.showToast === 'function') {
        window.showToast(message, 'error', 8000);
        return;
    }
    alert(message);
}

function showSuccess(message) {
    if (typeof window.showToast === 'function') {
        window.showToast(message, 'success', 5000);
        return;
    }
    alert(message);
}

function showInfo(message) {
    if (typeof window.showToast === 'function') {
        window.showToast(message, 'info', 6000);
        return;
    }
    alert(message);
}

/**
 * Bot Management Functions
 */
let allUserBots = [];
let selectedBotId = null;

async function loadMyBots() {
    try {
        showLoading();
        // Always fetch fresh data when loading My Bots section
        const response = await api.bots.getAll();
        allUserBots = response.bots || [];
        
        // Try to restore previously selected bot from localStorage
        const savedBotId = localStorage.getItem('selectedBotId');
        if (savedBotId && allUserBots.some(b => b.id === savedBotId)) {
            selectedBotId = savedBotId;
            console.log('[loadMyBots] Restored bot from localStorage:', savedBotId);
        } else {
            // Fall back to primary bot or first bot
            selectedBotId = response.primary_bot_id || (allUserBots.length > 0 ? allUserBots[0].id : null);
            console.log('[loadMyBots] Using primary or first bot:', selectedBotId);
        }
        
        console.log('Loaded bots:', allUserBots.length, 'bots');
        
        renderBotsGrid();
        populateBotSelectors();
    } catch (error) {
        console.error('Error loading bots:', error);
        showError('Failed to load your bots');
    } finally {
        hideLoading();
    }
}

function renderBotsGrid() {
    const botsGrid = document.getElementById('botsGrid');
    if (!botsGrid) return;
    
    console.log('renderBotsGrid called with', allUserBots.length, 'bots');
    
    if (allUserBots.length === 0) {
        botsGrid.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-robot"></i>
                <h3>No Companions Yet</h3>
                <p>You haven't created any AI companions yet. Visit the quiz page to create your first companion through our onboarding process.</p>
            </div>
        `;
        return;
    }
    
    console.log('Rendering', allUserBots.length, 'bot cards');
    botsGrid.innerHTML = allUserBots.map(bot => {
        console.log('Bot data:', bot);
        const archetypeNames = {
            'golden_retriever': 'Golden Retriever',
            'tsundere': 'Tsundere',
            'lawyer': 'Lawyer',
            'cool_girl': 'Cool Girl',
            'toxic_ex': 'Toxic Ex'
        };
        
        return `
            <div class="bot-card ${bot.is_primary ? 'primary' : ''}" data-bot-id="${bot.id}">
                <div class="bot-card-header">
                    <div class="bot-card-info">
                        <h3>${bot.bot_name}</h3>
                        <span class="archetype-badge">${archetypeNames[bot.archetype] || bot.archetype}</span>
                    </div>
                    <div class="bot-card-badges">
                        ${bot.is_primary ? '<span class="bot-badge primary"><i class="fas fa-star"></i> Primary</span>' : ''}
                        <span class="bot-badge ${bot.is_active ? 'active' : 'inactive'}">${bot.is_active ? 'Active' : 'Inactive'}</span>
                    </div>
                </div>
                
                <div class="bot-card-details">
                    <div class="bot-detail-item">
                        <label>Gender</label>
                        <span>${bot.bot_gender}</span>
                    </div>
                    <div class="bot-detail-item">
                        <label>Attachment</label>
                        <span>${bot.attachment_style}</span>
                    </div>
                    <div class="bot-detail-item">
                        <label>Flirtiness</label>
                        <span>${bot.flirtiness}</span>
                    </div>
                    <div class="bot-detail-item">
                        <label>Spice</label>
                        <span>${bot.toxicity}</span>
                    </div>
                </div>
                
                <div class="bot-card-actions">
                    <button class="btn btn-primary btn-small" onclick="showBotDetails('${bot.id}')">
                        <i class="fas fa-eye"></i>
                        View Details
                    </button>
                    <button class="btn btn-outline btn-small" onclick="editBotFromCard('${bot.id}')">
                        <i class="fas fa-cog"></i>
                        Settings
                    </button>
                    <button class="btn btn-danger btn-small" onclick="deleteBotConfirm('${bot.id}', '${bot.bot_name}')" style="background-color: #dc3545; border-color: #dc3545; color: white;">
                        <i class="fas fa-trash"></i>
                        Delete
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function populateBotSelectors() {
    const settingsBotSelect = document.getElementById('settingsBotSelect');
    if (settingsBotSelect && allUserBots.length > 0) {
        // Store the old listener function if it exists
        const oldChangeHandler = settingsBotSelect._changeHandler;
        
        // Remove old change event listener to prevent duplicates
        if (oldChangeHandler) {
            settingsBotSelect.removeEventListener('change', oldChangeHandler);
        }
        
        settingsBotSelect.innerHTML = allUserBots.map(bot => 
            `<option value="${bot.id}" ${bot.id === selectedBotId ? 'selected' : ''}>${bot.bot_name} (${bot.archetype})</option>`
        ).join('');
        
        // Set the dropdown value explicitly to selectedBotId
        settingsBotSelect.value = selectedBotId;
        console.log('[populateBotSelectors] Set dropdown to:', selectedBotId);
        
        // Create and store the change event listener
        const changeHandler = function() {
            selectedBotId = this.value;
            // Save selected bot to localStorage for persistence
            localStorage.setItem('selectedBotId', selectedBotId);
            console.log('[populateBotSelectors] Saved bot ID to localStorage:', selectedBotId);
            loadBotSettings(selectedBotId);
        };
        
        settingsBotSelect._changeHandler = changeHandler;
        settingsBotSelect.addEventListener('change', changeHandler);
    }
}

async function loadBotSettings(botId) {
    try {
        const bot = await api.bots.get(botId);
        selectedBotId = botId;
        
        // Save selected bot to localStorage for persistence
        localStorage.setItem('selectedBotId', botId);
        console.log('[loadBotSettings] Saved bot ID to localStorage:', botId);
        
        // Update dropdown selector to reflect the newly selected bot
        populateBotSelectors();
        
        // Populate settings form
        if (elements.settingBotName) elements.settingBotName.value = bot.bot_name || '';
        if (elements.settingGender) elements.settingGender.value = bot.bot_gender || 'female';
        if (elements.settingArchetype) elements.settingArchetype.value = bot.archetype || 'golden_retriever';
        if (elements.settingAttachment) elements.settingAttachment.value = bot.attachment_style || 'secure';
        if (elements.settingFlirtiness) elements.settingFlirtiness.value = bot.flirtiness || 'subtle';
        if (elements.settingToxicity) elements.settingToxicity.value = bot.toxicity || 'healthy';
        
        // Load advanced settings if available
        if (bot.advanced_settings && elements.advancedSettings) {
            renderAdvancedSettings(bot.advanced_settings);
        }
    } catch (error) {
        console.error('Error loading bot settings:', error);
        showError('Failed to load bot settings');
    }
}

function showCreateBotModal() {
    const modal = document.getElementById('createBotModal');
    if (modal) {
        modal.classList.add('active');
        
        // Setup form handlers
        const form = document.getElementById('createBotForm');
        const closeBtn = document.getElementById('closeCreateBotBtn');
        const cancelBtn = document.getElementById('cancelCreateBotBtn');
        
        if (form) {
            form.onsubmit = async (e) => {
                e.preventDefault();
                await createNewBot();
            };
        }
        
        if (closeBtn) closeBtn.onclick = () => modal.classList.remove('active');
        if (cancelBtn) cancelBtn.onclick = () => modal.classList.remove('active');
    }
}

async function createNewBot() {
    const botData = {
        bot_name: document.getElementById('newBotName').value,
        bot_gender: document.getElementById('newBotGender').value,
        archetype: document.getElementById('newBotArchetype').value,
        attachment_style: document.getElementById('newBotAttachment').value,
        flirtiness: document.getElementById('newBotFlirtiness').value,
        toxicity: document.getElementById('newBotToxicity').value
    };
    
    try {
        showLoading();
        const newBot = await api.bots.create(botData);
        showSuccess(`Bot "${newBot.bot_name}" created successfully!`);
        
        // Close modal
        document.getElementById('createBotModal').classList.remove('active');
        
        // Reload bots
        await loadMyBots();
        
        // Reset form
        document.getElementById('createBotForm').reset();
    } catch (error) {
        console.error('Error creating bot:', error);
        showError(error.message || 'Failed to create bot');
    } finally {
        hideLoading();
    }
}

async function showBotDetails(botId) {
    try {
        showLoading();
        const bot = await api.bots.get(botId);
        
        // Try to get telegram link, but don't fail if it returns 404
        let linkData = null;
        try {
            linkData = await api.bots.getTelegramLink(botId);
        } catch (error) {
            console.warn('Could not fetch telegram link for bot:', botId, error);
            // Continue without telegram link data - it will be handled below
        }
        
        // Populate modal
        const modal = document.getElementById('botDetailsModal');
        document.getElementById('botDetailsName').textContent = bot.bot_name;
        document.getElementById('detailsBotName').textContent = bot.bot_name;
        document.getElementById('detailsBotGender').textContent = bot.bot_gender;
        document.getElementById('detailsBotArchetype').textContent = bot.archetype;
        document.getElementById('detailsBotAttachment').textContent = bot.attachment_style;
        document.getElementById('detailsBotFlirtiness').textContent = bot.flirtiness;
        document.getElementById('detailsBotToxicity').textContent = bot.toxicity;
        
        // Set QR code only if linkData is available
        if (linkData && linkData.qr_code) {
            const qrImg = document.getElementById('botQRCode');
            const qrLoading = document.querySelector('.qr-loading');
            qrImg.src = linkData.qr_code;
            qrImg.style.display = 'block';
            if (qrLoading) qrLoading.style.display = 'none';
        }
        
        // Set Telegram link only if linkData is available
        if (linkData && linkData.deep_link) {
            document.getElementById('botTelegramLink').value = linkData.deep_link;
            document.getElementById('openTelegramBtn').href = linkData.deep_link;
        } else {
            // Hide or disable telegram link section if not available
            const telegramContainer = document.querySelector('.telegram-link-container');
            if (telegramContainer) {
                telegramContainer.style.display = 'none';
            }
            console.warn('Telegram link not available for bot:', bot.bot_name);
        }
        
        // Setup button handlers
        document.getElementById('editBotSettingsBtn').onclick = () => {
            modal.classList.remove('active');
            selectedBotId = botId;
            localStorage.setItem('selectedBotId', botId);
            navigateToSection('settings');
            loadBotSettings(botId);
        };
        
        document.getElementById('chatWithBotBtn').onclick = () => {
            modal.classList.remove('active');
            // Switch to this bot and go to chat
            selectedBotId = botId;
            localStorage.setItem('selectedBotId', selectedBotId);
            currentPersona = bot;
            updatePersonaUI();
            navigateToSection('chat');
        };
        
        document.getElementById('copyLinkBtn').onclick = () => {
            const linkInput = document.getElementById('botTelegramLink');
            if (!linkInput.value) {
                showError('Telegram link not available for this bot');
                return;
            }
            linkInput.select();
            document.execCommand('copy');
            showSuccess('Link copied to clipboard!');
        };
        
        document.getElementById('deleteBotBtn').onclick = () => {
            if (confirm(`Are you sure you want to delete "${bot.bot_name}"? This action cannot be undone.`)) {
                modal.classList.remove('active');
                deleteBot(botId);
            }
        };
        
        document.getElementById('closeBotDetailsBtn').onclick = () => {
            modal.classList.remove('active');
        };
        
        modal.classList.add('active');
    } catch (error) {
        console.error('Error loading bot details:', error);
        showError('Failed to load bot details');
    } finally {
        hideLoading();
    }
}

function editBotFromCard(botId) {
    selectedBotId = botId;
    navigateToSection('settings');
    loadBotSettings(botId);
}

function deleteBotConfirm(botId, botName) {
    if (confirm(`Are you sure you want to delete "${botName}"? This action cannot be undone.`)) {
        deleteBot(botId);
    }
}

async function deleteBot(botId) {
    try {
        showLoading();
        await api.bots.delete(botId);
        showSuccess('Bot deleted successfully!');
        
        // Remove from allUserBots array
        allUserBots = allUserBots.filter(b => b.id !== botId);
        
        // Close any open modals
        const modal = document.getElementById('botDetailsModal');
        if (modal) {
            modal.classList.remove('active');
        }
        
        // Reset selection if deleted bot was selected
        if (selectedBotId === botId) {
            selectedBotId = null;
            localStorage.removeItem('selectedBotId');
        }
        
        // Navigate to my-bots section and reload
        navigateToSection('my-bots');
        await loadMyBots();
    } catch (error) {
        console.error('Error deleting bot:', error);
        if (error.status === 403) {
            showError('Cannot delete your last bot. You must have at least one bot.');
        } else {
            showError('Failed to delete bot: ' + (error.message || 'Unknown error'));
        }
    } finally {
        hideLoading();
    }
}

// Update the saveSettings function to work with selected bot
async function saveBotSettings() {
    if (!selectedBotId) {
        showError('No bot selected');
        return;
    }
    
    // Collect basic settings
    const settings = {
        bot_name: elements.settingBotName?.value,
        bot_gender: elements.settingGender?.value,
        // archetype is not included as it cannot be changed
        attachment_style: elements.settingAttachment?.value,
        flirtiness: elements.settingFlirtiness?.value,
        toxicity: elements.settingToxicity?.value
    };
    
    // Collect advanced settings
    const advancedSettings = {};
    if (elements.advancedSettings) {
        const advancedInputs = elements.advancedSettings.querySelectorAll('select');
        advancedInputs.forEach(select => {
            const key = select.id.replace('advanced_', '');
            if (select.value) {
                advancedSettings[key] = select.value;
            }
        });
    }
    
    // Only add advanced_settings if there are any
    if (Object.keys(advancedSettings).length > 0) {
        settings.advanced_settings = advancedSettings;
    }
    
    try {
        showLoading();
        await api.bots.update(selectedBotId, settings);
        showSuccess('Bot settings saved successfully!');
        
        // Reload bots to reflect changes
        await loadMyBots();
        
        // If this is the current persona, update it
        if (currentPersona && currentPersona.id === selectedBotId) {
            currentPersona = await api.bots.get(selectedBotId);
            updatePersonaUI();
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showError('Failed to save settings');
    } finally {
        hideLoading();
    }
}

/**
 * Navigation Functions
 */
function showSettings() {
    navigateToSection('settings');
    // Also scroll to settings section
    setTimeout(() => {
        const settingsSection = document.getElementById('settings');
        if (settingsSection) {
            settingsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, 100);
}

function goToHome() {
    window.location.href = 'index.html';
}

/**
 * Logout Function
 */
async function logout() {
    if (isLoggingOut) return; // prevent double call
    isLoggingOut = true;

    try {
        // Clear token first to prevent any API calls from including it
        localStorage.removeItem('access_token');
        api.setToken(null);
        
        // Call logout endpoint (if it doesn't error, that's fine)
        await api.auth.logout().catch(() => {});
    } catch (err) {
        console.warn('Logout failed', err);
    }

    // Clear all local storage items
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_id');
    localStorage.removeItem('aiCompanionData');
    localStorage.removeItem('aiCompanionToken'); // compatibility
    localStorage.removeItem('dashboardSection'); // Clear dashboard section preference
    
    // Add a timestamp to signal other tabs
    localStorage.setItem('logout_timestamp', Date.now().toString());
    
    window.location.href = 'index.html';
}

// Export functions to global scope so they can be called from onclick handlers
// This is at the END of the file so all functions are defined first
window.navigateToSection = navigateToSection;
window.logout = logout;
window.goToHome = goToHome;
window.showSettings = showSettings;
window.showSupport = showSupport;
window.sendSupportMessage = sendSupportMessage;
window.closeSupportModal = closeSupportModal;
window.clearChat = clearChat;
window.handleMessageKeypress = handleMessageKeypress;
window.showCreateBotModal = showCreateBotModal;
window.showBotDetails = showBotDetails;
window.editBotFromCard = editBotFromCard;
window.deleteBotConfirm = deleteBotConfirm;
window.deleteBot = deleteBot;