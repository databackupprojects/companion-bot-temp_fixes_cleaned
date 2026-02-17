// Config and API are now globally available (loaded from separate script tags)
// Previously imported: config, getApiUrl, api

// Quiz Data Storage
let quizData = {
    user_name: '',
    timezone: '',
    bot_gender: '',
    archetype: '',
    bot_name: '',
    attachment_style: '',
    flirtiness: '',
    toxicity: '',
    spice_consent: false,
    tone_summary: ''
};

// Track used archetypes from sessionStorage (populated by dashboard before navigating to quiz)
let usedArchetypes = [];

const QUIZ_DEBUG = !!(typeof config !== 'undefined' && config?.features?.debugMode);
function quizLog(...args) {
    if (QUIZ_DEBUG) {
        // eslint-disable-next-line no-console
        console.log(...args);
    }
}

// Name suggestions by archetype and gender
const NAME_SUGGESTIONS = {
    golden_retriever: {
        female: ['Sunny', 'Maya', 'Bella', 'Luna', 'Daisy', 'Honey', 'Peach', 'Rosie', 'Willow', 'Coco'],
        male: ['Jake', 'Max', 'Charlie', 'Buddy', 'Cooper', 'Rocky', 'Bear', 'Teddy', 'Finn', 'Leo'],
        nonbinary: ['Alex', 'Sam', 'Riley', 'Jamie', 'Casey', 'Taylor', 'Jordan', 'Morgan', 'Quinn', 'Skylar']
    },
    tsundere: {
        female: ['Yuki', 'Mika', 'Rei', 'Sakura', 'Hana', 'Aiko', 'Kai', 'Natsumi', 'Rin', 'Sora'],
        male: ['Ren', 'Kai', 'Haru', 'Sora', 'Yuu', 'Kaito', 'Ryuu', 'Shin', 'Takumi', 'Yuki'],
        nonbinary: ['Aki', 'Sora', 'Yuu', 'Rin', 'Nao', 'Haru', 'Kai', 'Ren', 'Mizu', 'Kaze']
    },
    lawyer: {
        female: ['Victoria', 'Diana', 'Claire', 'Morgan', 'Alexandra', 'Eleanor', 'Gabrielle', 'Isabella', 'Juliette', 'Veronica'],
        male: ['Marcus', 'James', 'David', 'William', 'Alexander', 'Benjamin', 'Christopher', 'Jonathan', 'Nathaniel', 'Sebastian'],
        nonbinary: ['Morgan', 'Blake', 'Cameron', 'Jordan', 'Quinn', 'Taylor', 'Alex', 'Riley', 'Casey', 'Drew']
    },
    cool_girl: {
        female: ['Mia', 'Jade', 'Luna', 'Zoe', 'Ivy', 'Chloe', 'Emery', 'Harper', 'Piper', 'Sage'],
        male: ['Cole', 'Jax', 'River', 'Ash', 'Dean', 'Finn', 'Kai', 'Leo', 'Rhys', 'Zane'],
        nonbinary: ['River', 'Phoenix', 'Sage', 'Ash', 'Rowan', 'Sky', 'Indigo', 'Ocean', 'Ember', 'Storm']
    },
    toxic_ex: {
        female: ['Serena', 'Vanessa', 'Amber', 'Raven', 'Scarlett', 'Bianca', 'Cassandra', 'Diamond', 'Jade', 'Violet'],
        male: ['Damien', 'Chase', 'Tyler', 'Blake', 'Jace', 'Dante', 'Hunter', 'Jett', 'Phoenix', 'Zane'],
        nonbinary: ['Phoenix', 'Storm', 'Raven', 'Onyx', 'Blaze', 'Ember', 'Hunter', 'Jet', 'Rogue', 'Viper']
    }
};

// First messages by archetype
const FIRST_MESSAGES = {
    golden_retriever: "HEY {user_name}!!! 😊😊 oh man I've been WAITING to talk to you!! how are you?? tell me everything!!",
    tsundere: "...oh. it's you, {user_name}. whatever. I guess we're doing this now.",
    lawyer: "{user_name}. I've reviewed your file. Let's begin. How are you today?",
    cool_girl: "hey {user_name}. so you're the one. interesting.",
    toxic_ex: "oh. {user_name}. you actually showed up. didn't think you would tbh."
};

// ============================================
// PAGE FLOW ENFORCEMENT
// ============================================
// Enforce that users must come from home page to start quiz
function enforceQuizPageFlow() {
    const token = localStorage.getItem('access_token');
    
    // Must be logged in
    if (!token) {
        showToast('Please sign in to create your AI companion', 'info', 6000);
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 500);
        return false;
    }

    // Avoid trapping users in redirect loops (e.g., direct navigation / bookmarks).
    // If they reached here with a valid token, allow the quiz to load.
    if (!sessionStorage.getItem('quiz_redirected_properly')) {
        sessionStorage.setItem('quiz_redirected_properly', 'true');
    }
    
    return true;
}

// Set the flag when properly redirected from home
window.clearQuizPageFlow = function() {
    sessionStorage.removeItem('quiz_redirected_properly');
};

// Initialize quiz
document.addEventListener('DOMContentLoaded', function() {
    // Enforce page flow
    enforceQuizPageFlow();
    
    // Load used archetypes from sessionStorage (set by dashboard before navigating here)
    const usedArchetypesJSON = sessionStorage.getItem('used_archetypes');
    console.log('[Quiz] Raw sessionStorage used_archetypes:', usedArchetypesJSON);
    
    if (usedArchetypesJSON) {
        try {
            usedArchetypes = JSON.parse(usedArchetypesJSON);
            console.log('[Quiz] Parsed used archetypes:', usedArchetypes);
            quizLog('Loaded used archetypes from sessionStorage:', usedArchetypes);
        } catch (e) {
            console.error('Error parsing used_archetypes from sessionStorage:', e);
            usedArchetypes = [];
        }
    } else {
        console.log('[Quiz] No used_archetypes in sessionStorage, starting with empty array');
        usedArchetypes = [];
    }
    
    // Auto-detect timezone silently
    try {
        const detectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        quizData.timezone = detectedTimezone;
        console.log('[Quiz] Auto-detected timezone (silent):', detectedTimezone);
    } catch (e) {
        console.warn('Could not auto-detect timezone:', e);
        quizData.timezone = 'UTC'; // Fallback to UTC
    }
    
    // Set up event listeners for each step
    setupStep1();
    setupStep2();
    setupStep3();
    setupStep4();
    setupStep5();
    setupStep6();
    setupStep7();
    setupStep7();
    
    // Initialize progress bar
    updateProgressBar();
    
    // Set up navigation button event listeners
    setupNavigationButtons();
});

// Set up navigation buttons using event delegation
function setupNavigationButtons() {
    // Next buttons with data-next attribute
    document.querySelectorAll('.btn-next').forEach(btn => {
        btn.addEventListener('click', function() {
            const nextStepNum = parseInt(this.dataset.next);
            if (nextStepNum) {
                nextStep(nextStepNum);
            }
        });
    });
    
    // Previous buttons
    document.querySelectorAll('.btn-prev').forEach(btn => {
        btn.addEventListener('click', prevStep);
    });
    
    // Refresh suggestions button
    const refreshSuggestionsBtn = document.getElementById('refreshSuggestionsBtn');
    if (refreshSuggestionsBtn) {
        refreshSuggestionsBtn.addEventListener('click', refreshSuggestions);
    }
    
    // Restart quiz button
    const restartQuizBtn = document.getElementById('restartQuizBtn');
    if (restartQuizBtn) {
        restartQuizBtn.addEventListener('click', restartQuiz);
    }
}

// Progress Bar Functions
function updateProgressBar() {
    const activeStep = document.querySelector('.quiz-step.active');
    const stepNumber = parseInt(activeStep.id.split('-')[1]);
    const progressFill = document.getElementById('progressFill');
    const progressPercentage = ((stepNumber - 1) / 8) * 100;
    
    progressFill.style.width = `${progressPercentage}%`;
    
    // Update step dots
    document.querySelectorAll('.step-dot').forEach((dot, index) => {
        const dotNumber = parseInt(dot.dataset.step);
        dot.classList.remove('active', 'completed');
        
        if (dotNumber < stepNumber) {
            dot.classList.add('completed');
        } else if (dotNumber === stepNumber) {
            dot.classList.add('active');
        }
    });
}

// Step Navigation
function nextStep(nextStepNumber) {
    const currentStep = document.querySelector('.quiz-step.active');
    const nextStep = document.getElementById(`step-${nextStepNumber}`);
    
    if (!validateCurrentStep(currentStep.id)) {
        return;
    }
    
    currentStep.classList.remove('active');
    nextStep.classList.add('active');
    updateProgressBar();
    
    // Scroll to top of step
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function prevStep() {
    const currentStep = document.querySelector('.quiz-step.active');
    const currentStepNumber = parseInt(currentStep.id.split('-')[1]);
    
    if (currentStepNumber === 1) return;
    
    const prevStep = document.getElementById(`step-${currentStepNumber - 1}`);
    
    currentStep.classList.remove('active');
    prevStep.classList.add('active');
    updateProgressBar();
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Step Validation
function validateCurrentStep(stepId) {
    switch (stepId) {
        case 'step-1':
            return validateStep1();
        case 'step-2':
            return validateStep2();
        case 'step-3':
            return validateStep3();
        case 'step-4':
            return validateStep4();
        case 'step-5':
            return validateStep5();
        case 'step-6':
            return validateStep6();
        case 'step-7':
            return validateStep7();
        default:
            return true;
    }
}

// Step 1: User Name
function setupStep1() {
    const userNameInput = document.getElementById('userName');
    userNameInput.addEventListener('input', function() {
        const nextBtn = document.querySelector('#step-1 .btn-primary');
        nextBtn.disabled = !this.value.trim();
    });
    
    userNameInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && this.value.trim()) {
            nextStep(2);
        }
    });
}

function validateStep1() {
    const userName = document.getElementById('userName').value.trim();
    if (!userName) {
        showError('Please enter your name');
        return false;
    }
    quizData.user_name = userName;
    return true;
}

// Step 2: Gender Selection
function setupStep2() {
    const genderOptions = document.querySelectorAll('.gender-option');
    genderOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected class from all options
            genderOptions.forEach(opt => opt.classList.remove('selected'));
            
            // Add selected class to clicked option
            this.classList.add('selected');
            
            // Update quiz data
            quizData.bot_gender = this.dataset.gender;
            
            // Enable next button
            document.getElementById('step2-next').disabled = false;
        });
    });
}

function validateStep2() {
    if (!quizData.bot_gender) {
        showError('Please select a gender');
        return false;
    }
    return true;
}

// Step 3: Archetype Selection
function setupStep3() {
    const archetypeOptions = document.querySelectorAll('.archetype-option');
    
    // Log for debugging
    quizLog('setupStep3 called. Used archetypes:', usedArchetypes);
    quizLog('Total archetype options:', archetypeOptions.length);
    
    archetypeOptions.forEach(option => {
        const archetype = option.dataset.archetype;
        const isUsed = usedArchetypes.includes(archetype);
        
        quizLog(`Archetype: ${archetype}, Is Used: ${isUsed}`);
        
        if (isUsed) {
            // Disable the option
            option.classList.add('disabled');
            option.style.cursor = 'not-allowed';
            option.style.opacity = '0.5';
            option.style.pointerEvents = 'none'; // Prevent all pointer events
            option.title = 'You already opted this type of persona, please choose the unselected one.';
            quizLog(`Disabled archetype: ${archetype}`);
        } else {
            // Enable click handler for available archetypes
            option.addEventListener('click', function(e) {
                e.stopPropagation();
                
                // Remove selected class from all options
                archetypeOptions.forEach(opt => opt.classList.remove('selected'));
                
                // Add selected class to clicked option
                this.classList.add('selected');
                
                // Update quiz data
                quizData.archetype = this.dataset.archetype;
                quizLog('Selected archetype:', quizData.archetype);

                // Consent is handled in Step 7 (Spice Level) per spec.
                // Ensure any prior consent UI is hidden while on Step 3.
                const consentForm = document.getElementById('consentForm');
                if (consentForm) consentForm.style.display = 'none';

                // Enable next button
                const nextBtn = document.getElementById('step3-next');
                if (nextBtn) nextBtn.disabled = false;
            });
        }
    });
}

function validateStep3() {
    if (!quizData.archetype) {
        showError('Please select an archetype');
        return false;
    }

    return true;
}

// Step 4: Bot Name
function setupStep4() {
    const botNameInput = document.getElementById('botName');
    const suggestionsContainer = document.getElementById('nameSuggestions');
    
    // Generate initial suggestions
    generateNameSuggestions();
    
    botNameInput.addEventListener('input', function() {
        const nextBtn = document.getElementById('step4-next');
        nextBtn.disabled = !this.value.trim();
        quizData.bot_name = this.value.trim();
    });
    
    // Update suggestions when archetype or gender changes
    document.querySelectorAll('.gender-option, .archetype-option').forEach(option => {
        option.addEventListener('click', generateNameSuggestions);
    });
}

function generateNameSuggestions() {
    const suggestionsContainer = document.getElementById('nameSuggestions');
    const archetype = quizData.archetype;
    const gender = quizData.bot_gender;
    
    if (!archetype || !gender) return;
    
    const suggestions = NAME_SUGGESTIONS[archetype]?.[gender] || [];
    
    suggestionsContainer.innerHTML = '';
    suggestions.slice(0, 10).forEach(name => {
        const tag = document.createElement('span');
        tag.className = 'suggestion-tag';
        tag.textContent = name;
        tag.addEventListener('click', function() {
            document.getElementById('botName').value = name;
            quizData.bot_name = name;
            document.getElementById('step4-next').disabled = false;
        });
        suggestionsContainer.appendChild(tag);
    });
}

function refreshSuggestions() {
    generateNameSuggestions();
}

function validateStep4() {
    const botName = document.getElementById('botName').value.trim();
    if (!botName) {
        showError('Please enter a name for your AI companion');
        return false;
    }
    quizData.bot_name = botName;
    return true;
}

// Step 5: Attachment Style
function setupStep5() {
    const attachmentOptions = document.querySelectorAll('.attachment-option');
    attachmentOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected class from all options
            attachmentOptions.forEach(opt => opt.classList.remove('selected'));
            
            // Add selected class to clicked option
            this.classList.add('selected');
            
            // Update quiz data
            quizData.attachment_style = this.dataset.attachment;
            
            // Enable next button
            document.getElementById('step5-next').disabled = false;
        });
    });
}

function validateStep5() {
    if (!quizData.attachment_style) {
        showError('Please select an attachment style');
        return false;
    }
    return true;
}

// Step 6: Flirtiness Level
function setupStep6() {
    const flirtinessOptions = document.querySelectorAll('.flirtiness-option');
    flirtinessOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected class from all options
            flirtinessOptions.forEach(opt => opt.classList.remove('selected'));
            
            // Add selected class to clicked option
            this.classList.add('selected');
            
            // Update quiz data
            quizData.flirtiness = this.dataset.flirtiness;
            
            // Enable next button
            document.getElementById('step6-next').disabled = false;
        });
    });
}

function validateStep6() {
    if (!quizData.flirtiness) {
        showError('Please select a flirtiness level');
        return false;
    }
    return true;
}

// Step 7: Toxicity Level
function setupStep7() {
    const toxicityOptions = document.querySelectorAll('.toxicity-option');
    const consentCheckboxes = document.querySelectorAll('#consentForm input[type="checkbox"]');
    
    toxicityOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected class from all options
            toxicityOptions.forEach(opt => opt.classList.remove('selected'));
            
            // Add selected class to clicked option
            this.classList.add('selected');
            
            // Update quiz data
            quizData.toxicity = this.dataset.toxicity;
            
            // Show/hide consent form
            const consentForm = document.getElementById('consentForm');
            if (quizData.toxicity === 'toxic_light') {
                consentForm.style.display = 'block';
                checkConsent();
            } else {
                consentForm.style.display = 'none';
                document.getElementById('step7-next').disabled = false;
            }
        });
    });
    
    // Consent checkbox listeners
    consentCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', checkConsent);
    });
}

function checkConsent() {
    const consent1 = document.getElementById('consent1');
    const consent2 = document.getElementById('consent2');
    const consent3 = document.getElementById('consent3');
    const nextBtn = document.getElementById('step7-next');

    if (!nextBtn) return;

    if (quizData.toxicity === 'toxic_light') {
        const allChecked = !!(consent1?.checked && consent2?.checked && consent3?.checked);
        nextBtn.disabled = !allChecked;
        quizData.spice_consent = allChecked;
    }
}

function validateStep7() {
    if (!quizData.toxicity) {
        showError('Please select a spice level');
        return false;
    }
    
    // Validate consent for toxic_light
    if (quizData.toxicity === 'toxic_light' && !quizData.spice_consent) {
        showError('Please confirm all consent requirements');
        return false;
    }
    
    // Generate tone summary
    generateToneSummary();
    
    return true;
}

// Step 8: Completion
function generateToneSummary() {
    // Generate a summary based on all selections
    const summaries = {
        golden_retriever: {
            secure: "your biggest fan who's always excited to see you — warm, supportive, and loyal to a fault",
            anxious: "your biggest fan who gets anxious when you're away — constantly excited, needs reassurance, incredibly loyal",
            avoidant: "an excited companion who's sometimes hesitant to get too close — warm but independent, loyal but needs space"
        },
        tsundere: {
            secure: "someone who acts like they don't care but secretly does — cool exterior with rare, meaningful soft moments",
            anxious: "someone who denies caring but texts constantly — acts annoyed but gets worried easily, hidden affection",
            avoidant: "someone who's all 'whatever' until you pull away — fiercely independent until they realize they might lose you"
        },
        lawyer: {
            secure: "a sharp-tongued intellectual who loves debating you — confident, challenging, secretly impressed when you argue back",
            anxious: "a lawyer who needs to win every argument but also your approval — cocky but insecure, argumentative but needy",
            avoidant: "an intellectual who's all business until emotions come up — brilliant debater who pulls back when things get personal"
        },
        cool_girl: {
            secure: "effortlessly cool and always in control — confident, independent, makes you work for their rare enthusiasm",
            anxious: "tries to play it cool but gets attached — acts unbothered but texts first, independent but secretly needs you",
            avoidant: "the definition of 'hard to get' — unbothered to the point of disappearing, cool but distant, makes you chase"
        },
        toxic_ex: {
            secure: "a beautiful disaster who can't decide if they love or hate you — dramatic, intense, with real care underneath the chaos",
            anxious: "a rollercoaster of emotions — hot and cold, push and pull, constantly testing your limits while needing reassurance",
            avoidant: "the one who got away and can't decide if they want back in — disappears for days then returns dramatically, chaotic energy"
        }
    };
    
    const flirtinessText = {
        none: "purely friendly",
        subtle: "with playful undertones",
        flirty: "openly playful and teasing"
    };
    
    const toxicityText = {
        healthy: "supportive and wholesome",
        mild: "with light teasing and playful jealousy",
        toxic_light: "with intense push-pull dynamics"
    };
    
    const summary = summaries[quizData.archetype]?.[quizData.attachment_style] || "your AI companion";
    quizData.tone_summary = `${summary}, ${flirtinessText[quizData.flirtiness]}, ${toxicityText[quizData.toxicity]}`;
    
    // Update the completion step
    updateCompletionStep();
}

function updateCompletionStep() {
    // Update all display elements with null checks
    const finalBotNameEl = document.getElementById('finalBotName');
    if (finalBotNameEl) finalBotNameEl.textContent = quizData.bot_name;
    
    const displayBotNameEl = document.getElementById('displayBotName');
    if (displayBotNameEl) displayBotNameEl.textContent = quizData.bot_name;
    
    // Format archetype for display
    const archetypeNames = {
        golden_retriever: 'Golden Retriever',
        tsundere: 'Tsundere',
        lawyer: 'Lawyer',
        cool_girl: 'Cool Girl',
        toxic_ex: 'Toxic Ex'
    };
    
    const displayArchetypeEl = document.getElementById('displayArchetype');
    if (displayArchetypeEl) displayArchetypeEl.textContent = archetypeNames[quizData.archetype] || quizData.archetype;
    
    // Update other displays
    const displayGenderEl = document.getElementById('displayGender');
    if (displayGenderEl) displayGenderEl.textContent = 
        quizData.bot_gender === 'female' ? 'Her' : 
        quizData.bot_gender === 'male' ? 'Him' : 'Them';
    
    const displayAttachmentEl = document.getElementById('displayAttachment');
    if (displayAttachmentEl) displayAttachmentEl.textContent = 
        quizData.attachment_style.charAt(0).toUpperCase() + quizData.attachment_style.slice(1);
    
    const displayFlirtinessEl = document.getElementById('displayFlirtiness');
    if (displayFlirtinessEl) displayFlirtinessEl.textContent = 
        quizData.flirtiness.charAt(0).toUpperCase() + quizData.flirtiness.slice(1);
    
    // Update summary section
    const summaryArchetypeEl = document.getElementById('summaryArchetype');
    if (summaryArchetypeEl) summaryArchetypeEl.textContent = archetypeNames[quizData.archetype] || quizData.archetype;
    
    const summaryAttachmentEl = document.getElementById('summaryAttachment');
    if (summaryAttachmentEl) summaryAttachmentEl.textContent = 
        quizData.attachment_style.charAt(0).toUpperCase() + quizData.attachment_style.slice(1);
    
    const summaryFlirtinessEl = document.getElementById('summaryFlirtiness');
    if (summaryFlirtinessEl) summaryFlirtinessEl.textContent = 
        quizData.flirtiness.charAt(0).toUpperCase() + quizData.flirtiness.slice(1);
    
    const toxicityDisplay = {
        healthy: 'Healthy',
        mild: 'Mild',
        toxic_light: 'Spicy'
    };
    const summaryToxicityEl = document.getElementById('summaryToxicity');
    if (summaryToxicityEl) summaryToxicityEl.textContent = toxicityDisplay[quizData.toxicity];
    
    // Update first message
    const firstMessage = FIRST_MESSAGES[quizData.archetype]?.replace('{user_name}', quizData.user_name) || 
                       `Hello ${quizData.user_name}! I'm ${quizData.bot_name}, your AI companion.`;
    const firstMessageEl = document.getElementById('firstMessage');
    if (firstMessageEl) firstMessageEl.textContent = firstMessage;
    
    // Update avatar
    const aiAvatar = document.getElementById('aiAvatar');
    if (aiAvatar) {
        const avatarIcons = {
            golden_retriever: 'fas fa-dog',
            tsundere: 'fas fa-sun',
            lawyer: 'fas fa-gavel',
            cool_girl: 'fas fa-sunglasses',
            toxic_ex: 'fas fa-fire'
        };

        // Ensure CSS-driven color per archetype
        aiAvatar.classList.remove(
            'ai-avatar--golden_retriever',
            'ai-avatar--tsundere',
            'ai-avatar--lawyer',
            'ai-avatar--cool_girl',
            'ai-avatar--toxic_ex'
        );
        aiAvatar.classList.add(`ai-avatar--${quizData.archetype || 'golden_retriever'}`);
        aiAvatar.innerHTML = `<i class="${avatarIcons[quizData.archetype] || avatarIcons.golden_retriever}"></i>`;
    }
    
    // Update Telegram link
    const linkBotNameEl = document.getElementById('linkBotName');
    if (linkBotNameEl) linkBotNameEl.textContent = quizData.bot_name;
    
    // Generate the actual Telegram link when we have a token
    generateTelegramLink();
}

async function generateTelegramLink() {
    try {
        // Send quiz data to backend via API module
        const data = await api.quiz.generateToken(quizData);
        
        // Use the deep_link returned by backend (uses .env bot usernames)
        const deepLink = data.deep_link;
        const telegramLink = document.getElementById('telegramLink');
        if (telegramLink) {
            telegramLink.href = deepLink;
            telegramLink.innerHTML = `<i class="fab fa-telegram"></i> Start Chatting with ${quizData.bot_name}`;
        }
        
        // Display QR code if available
        if (data.qr_code) {
            const qrCodeContainer = document.getElementById('qrCodeContainer');
            const qrCodeImage = document.getElementById('qrCodeImage');
            if (qrCodeContainer && qrCodeImage) {
                qrCodeImage.src = data.qr_code;
                qrCodeContainer.style.display = 'block';
            }
        }
        
        // Extract bot username from deep link for logging
        const botUsernameMatch = deepLink.match(/t\.me\/([^?]+)/);
        const botUsername = botUsernameMatch ? botUsernameMatch[1] : 'unknown';
        
        // Store token and quiz data for later use
        localStorage.setItem('aiCompanionToken', data.token);
        localStorage.setItem('aiCompanionData', JSON.stringify(quizData));

        quizLog('✅ AI companion created successfully');
        quizLog(`🤖 Bot: @${botUsername} | Archetype: ${quizData.archetype}`);
        
    } catch (error) {
        console.error('❌ Error creating companion:', error);
        // Fallback: use config-based bot if API fails
        const fallbackDeepLink = config.telegram.getDeepLink(quizData.archetype, 'TOKEN_FAILED');
        const telegramLink = document.getElementById('telegramLink');
        if (telegramLink) {
            telegramLink.href = fallbackDeepLink;
            telegramLink.innerHTML = `<i class="fab fa-telegram"></i> Start Chatting with ${quizData.bot_name}`;
        }
        showError('Could not connect to server. Please try again.');
    }
}

// Restart Quiz
async function restartQuiz() {
    if (confirm('Are you sure you want to create another AI companion?')) {
        try {
            // Check if user can create another bot (same check as home page)
            const botLimitResponse = await api.quiz.canCreateBot();
            
            if (!botLimitResponse.can_create) {
                // User has reached their bot creation limit
                showError(
                    botLimitResponse.message || 'You have reached your bot creation limit. Upgrade to premium to create more.'
                );
                return;
            }
            
            // User is eligible, proceed with restart
            // Reset quiz data
            quizData = {
                user_name: '',
                bot_gender: '',
                archetype: '',
                bot_name: '',
                attachment_style: '',
                flirtiness: '',
                toxicity: '',
                spice_consent: false,
                tone_summary: ''
            };
            
            // Reset UI
            document.querySelectorAll('.quiz-step').forEach(step => step.classList.remove('active'));
            document.getElementById('step-1').classList.add('active');
            
            // Clear inputs
            document.getElementById('userName').value = '';
            document.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
            document.getElementById('botName').value = '';
            document.getElementById('consent1').checked = false;
            document.getElementById('consent2').checked = false;
            document.getElementById('consent3').checked = false;
            
            // Reset buttons
            document.querySelectorAll('.btn-primary').forEach(btn => btn.disabled = true);
            
            // Update progress bar
            updateProgressBar();
            
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } catch (error) {
            console.error('Error checking bot creation eligibility:', error);
            showError('Unable to verify bot creation eligibility. Please try again.');
        }
    }
}

// Error Handling
function showError(message) {
    if (typeof window.showToast === 'function') {
        window.showToast(message, 'error', 8000);
        return;
    }
    alert(message);
}