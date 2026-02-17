// frontend/scripts/main.js
// Mobile navigation toggle and accessibility handlers

const DEBUG = (typeof config !== 'undefined' && config?.features?.debugMode)
  || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

function debugLog(...args) {
  if (DEBUG) console.log(...args);
}

function debugWarn(...args) {
  if (DEBUG) console.warn(...args);
}

// ============================================
// AUTHENTICATION GUARDS
// ============================================
window.enforceAuth = function() {
  const token = localStorage.getItem('access_token');
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  
  // Pages that don't require authentication
  const publicPages = ['index.html', 'login.html', 'signup.html', ''];
  
  // If logged out and trying to access protected page, redirect to login
  if (!token && !publicPages.includes(currentPage)) {
    showToast('Please sign in to access this page', 'info', 6000);
    setTimeout(() => {
      window.location.href = 'login.html';
    }, 500);
    return false;
  }
  
  return true;
};

// Check auth on page load
document.addEventListener('DOMContentLoaded', function() {
  enforceAuth();
  
  // Add event listeners for quiz links
  document.querySelectorAll('.quiz-link').forEach(link => {
    link.addEventListener('click', window.checkAuthAndNavigateToQuiz);
  });
});

// ============================================
// TOAST NOTIFICATION SYSTEM (FIXED, SINGLE SOURCE)
// ============================================
window.showToast = function (message, type = 'info', duration = 6000) {
  let toastContainer = document.getElementById('toast-container');

  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const iconMap = {
    success: 'fa-check-circle',
    error: 'fa-exclamation-circle',
    warning: 'fa-warning',
    info: 'fa-info-circle'
  };

  toast.innerHTML = `
    <i class="fas ${iconMap[type]}"></i>
    <span class="toast-message">${message}</span>
    <button class="toast-close" type="button" aria-label="Close notification">
      <i class="fas fa-times"></i>
    </button>
  `;

  toastContainer.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add('toast-visible');
  });

  let remaining = duration;
  let startTime = Date.now();
  let timer;

  const closeToast = () => {
    toast.classList.remove('toast-visible');
    setTimeout(() => toast.remove(), 250);
  };

  const startTimer = () => {
    if (remaining <= 0) return;
    startTime = Date.now();
    timer = setTimeout(closeToast, remaining);
  };

  const pauseTimer = () => {
    if (!timer) return;
    clearTimeout(timer);
    remaining -= Date.now() - startTime;
  };

  // 🔧 Pause on hover
  toast.addEventListener('mouseenter', pauseTimer);
  toast.addEventListener('mouseleave', startTimer);

  // Close button
  toast.querySelector('button').addEventListener('click', closeToast);

  startTimer();
};

// ============================================
// AUTH CHECK FOR QUIZ NAVIGATION (UNCHANGED)
// ============================================
window.checkAuthAndNavigateToQuiz = async function (event) {
  event.preventDefault();

  const token = localStorage.getItem('access_token');

  if (!token) {
    showToast(
      'Sign up or sign in to create your AI companion',
      'info',
      10000
    );

    setTimeout(() => {
      window.location.href = 'login.html';
    }, 2500);
    return;
  }

  try {
    const botLimitResponse = await api.quiz.canCreateBot();
    if (botLimitResponse.can_create) {
      // Set session flag to indicate proper redirect from home page
      sessionStorage.setItem('quiz_redirected_properly', 'true');
      window.location.href = 'quiz.html';
    } else {
      showToast(
        botLimitResponse.message || 'You have reached your bot creation limit',
        'warning',
        12000
      );
    }
  } catch (error) {
    console.error('Error checking bot limit:', error);
    // Set flag anyway to allow fallback
    sessionStorage.setItem('quiz_redirected_properly', 'true');
    window.location.href = 'quiz.html';
  }
};

document.addEventListener('DOMContentLoaded', function () {
  const navToggle = document.getElementById('navToggle');
  const navMenu = document.querySelector('.nav-menu');

  if (!navToggle || !navMenu) return;

  // Compatibility shim: some legacy code uses `aiCompanionToken`
  if (!localStorage.getItem('access_token') && localStorage.getItem('aiCompanionToken')) {
    localStorage.setItem('access_token', localStorage.getItem('aiCompanionToken'));
  }

  // Toggle mobile menu
  let navBackdrop = null;
  const createBackdrop = () => {
    const backdrop = document.createElement('div');
    backdrop.className = 'nav-backdrop';
    backdrop.addEventListener('click', () => toggleMenu(false));
    document.body.appendChild(backdrop);
    return backdrop;
  };

  const removeBackdrop = () => {
    if (navBackdrop && navBackdrop.parentNode) {
      navBackdrop.parentNode.removeChild(navBackdrop);
      navBackdrop = null;
    }
  };

  const toggleMenu = (open) => {
    const isOpen = typeof open === 'boolean' ? open : !navMenu.classList.contains('mobile-open');

    if (isOpen) {
      navMenu.classList.add('mobile-open');
      navToggle.setAttribute('aria-expanded', 'true');
      navToggle.classList.add('open');
      document.body.classList.add('menu-open');

      // create backdrop
      if (!navBackdrop) navBackdrop = createBackdrop();

      // focus first interactive element in menu for accessibility
      const firstInteractive = navMenu.querySelector('a, button');
      if (firstInteractive) firstInteractive.focus();
    } else {
      navMenu.classList.remove('mobile-open');
      navToggle.setAttribute('aria-expanded', 'false');
      navToggle.classList.remove('open');
      document.body.classList.remove('menu-open');

      removeBackdrop();

      // return focus to toggle for keyboard users
      navToggle.focus();
    }
  };

  navToggle.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleMenu();
  });

  // Delegate link clicks inside nav to handle dynamic items (hash scrolling & mobile close)
  navMenu.addEventListener('click', (e) => {
    const link = e.target.closest('a[href]');
    if (!link) return;
    const href = link.getAttribute('href');
    debugLog('[NAV] Link clicked - href:', href);

    // Skip handling for empty/hash-only links
    if (!href || href === '#') {
      debugLog('[NAV] Skipping empty/hash-only href');
      return;
    }

    // For page navigation links (not hash anchors), just close menu and let natural navigation happen
    if (!href.startsWith('#')) {
      debugLog('[NAV] Page navigation link detected:', href);
      // Close the mobile menu when navigating away
      toggleMenu(false);
      // Let the link navigate naturally - don't prevent default
      return;
    }

    // Handle hash links (anchor scrolling)
    if (href.startsWith('#') && href.length > 1) {
      debugLog('[NAV] Hash anchor detected:', href);
      e.preventDefault();
      const target = document.querySelector(href);

      // Close menu then scroll to target with navbar offset
      toggleMenu(false);
      setTimeout(() => {
        if (target) {
          const navbar = document.querySelector('.navbar');
          const offset = navbar ? navbar.offsetHeight + 8 : 8;
          const y = target.getBoundingClientRect().top + window.pageYOffset - offset;
          window.scrollTo({ top: y, behavior: 'smooth' });

          // focus target for accessibility
          try { target.setAttribute('tabindex', '-1'); } catch (err) {}
          try { target.focus(); } catch (err) {}
        }
      }, 300);
    }
  });

  // Close menu on outside click
  document.addEventListener('click', (e) => {
    const target = e.target;
    if (!navMenu.contains(target) && !navToggle.contains(target) && navMenu.classList.contains('mobile-open')) {
      toggleMenu(false);
    }
  });

  // Close on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && navMenu.classList.contains('mobile-open')) {
      toggleMenu(false);
    }
  });

  // Improve keyboard experience: open menu with Enter/Space when focused on toggle
  navToggle.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleMenu();
    }
  });

  // Ensure ARIA defaults
  navToggle.setAttribute('aria-controls', 'primary-navigation');
  navToggle.setAttribute('aria-expanded', 'false');
  navMenu.setAttribute('id', 'primary-navigation');

  // Close mobile menu when resizing to desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768 && navMenu.classList.contains('mobile-open')) {
      toggleMenu(false);
    }
  });

  // -------------------- Sign Up modal handlers --------------------
  const signupModal = document.getElementById('signupModal');
  const signupBackdrop = document.getElementById('signupBackdrop');
  const signupClose = document.getElementById('signupClose');
  const signupForm = document.getElementById('signupForm');
  const signupError = document.getElementById('signupError');

  const openSignup = () => {
    const signupBtn = document.getElementById('signupBtn');
    if (signupModal) signupModal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
    const firstInput = document.getElementById('signupUsername');
    if (firstInput) firstInput.focus();
  };

  const closeSignup = () => {
    const signupBtn = document.getElementById('signupBtn');
    if (signupModal) signupModal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');
    if (signupError) signupError.textContent = '';
    if (signupForm) signupForm.reset();
    if (signupBtn) signupBtn.focus();
  };

  if (signupBackdrop) {
    signupBackdrop.addEventListener('click', closeSignup);
  }
  if (signupClose) {
    signupClose.addEventListener('click', closeSignup);
  }

  // Helper to attach auth buttons behavior to current DOM nodes
  function attachAuthHandlers() {
    const signupBtn = document.getElementById('signupBtn');
    const loginBtn = document.getElementById('loginBtn');

    if (signupBtn) {
      signupBtn.removeEventListener('click', openSignup);
      signupBtn.addEventListener('click', (e) => { e.preventDefault(); openSignup(); });
    }

    if (loginBtn) {
      // remove any prior handlers by replacing the node
      const newLogin = loginBtn.cloneNode(true);
      loginBtn.parentNode.replaceChild(newLogin, loginBtn);
      newLogin.addEventListener('click', (e) => { e.preventDefault(); openLogin(); });
    }
  }

  // Render signed-out UI: ensure Login and Sign Up exist and are wired
  function renderSignedOutUI() {
    const navAuth = document.querySelector('.nav-auth');
    if (!navAuth) return;

    // ensure signup exists
    navAuth.innerHTML = '';
    if (!document.getElementById('signupBtn')) {
      const btn = document.createElement('a');
      btn.className = 'btn btn-primary';
      btn.id = 'signupBtn';
      btn.href = '#';
      btn.textContent = 'Sign Up';
      navAuth.appendChild(btn);
    }

    // ensure login exists
    if (!document.getElementById('loginBtn')) {
      const btn = document.createElement('a');
      btn.className = 'btn btn-outline';
      btn.id = 'loginBtn';
      btn.href = '#';
      btn.textContent = 'Login';
      navAuth.appendChild(btn);
    }

    attachAuthHandlers();

    // hide footer dashboard link when signed out
    updateFooterDashboardVisibility(false);
  }

  // Submit sign up form
  if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (signupError) signupError.textContent = '';

      const username = document.getElementById('signupUsername').value.trim();
      const email = document.getElementById('signupEmail').value.trim();
      const password = document.getElementById('signupPassword').value;
      const confirm = document.getElementById('signupPasswordConfirm').value;

      if (!username || !email || !password) {
        if (signupError) signupError.textContent = 'Username, email, and password are required.';
        return;
      }

      if (password !== confirm) {
        if (signupError) signupError.textContent = 'Passwords do not match.';
        return;
    }

    // Submit to API
    signupError.textContent = '';
    const payload = { username, email, password };

    const submitBtn = document.getElementById('signupSubmit');
    submitBtn.disabled = true;
    const originalLabel = submitBtn.textContent;
    submitBtn.textContent = 'Creating...';

    const registerUrl = `${config.api.baseURL}/api/auth/register`;

    try {
      const res = await fetch(registerUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });

      if (res.ok) {
        const data = await res.json();
        // Save token and username for persistence
        if (data && data.access_token) {
          localStorage.setItem('access_token', data.access_token);
          // compatibility shim for legacy code
          localStorage.setItem('aiCompanionToken', data.access_token);
          if (data.user_id) localStorage.setItem('user_id', data.user_id);
          // backend may return username/email
          if (data.username) localStorage.setItem('user_name', data.username);
          else localStorage.setItem('user_name', username);
        }

        signupError.textContent = '';
        closeSignup();
        // Non-blocking success toast
        showToast('Account created successfully! You are now signed in.', 'success');

        // Update UI with signed-in user
        setSignedInUI();
        updateFooterDashboardVisibility(true);
      } else {
        const err = await res.json().catch(() => ({}));
        if (signupError) signupError.textContent = err.detail || (err.error || 'Failed to create account.');
      }

    } catch (err) {
      console.error('Sign up error', err);
      if (signupError) signupError.textContent = 'Network error. Try again.';
    } finally {
      // restore submit button
      submitBtn.disabled = false;
      submitBtn.textContent = originalLabel;
    }
    });
  }

  // -------------------- Login modal handlers & auth UI --------------------
  const loginBtn = document.getElementById('loginBtn');
  const loginModal = document.getElementById('loginModal');
  const loginBackdrop = document.getElementById('loginBackdrop');
  const loginClose = document.getElementById('loginClose');
  const loginForm = document.getElementById('loginForm');
  const loginError = document.getElementById('loginError');

  const openLogin = () => {
    if (loginModal) loginModal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
    const firstInput = document.getElementById('loginEmail');
    if (firstInput) firstInput.focus();
  };

  const closeLogin = () => {
    if (loginModal) loginModal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');
    if (loginError) loginError.textContent = '';
    if (loginForm) loginForm.reset();
    if (loginBtn) loginBtn.focus();
  };

  if (loginBtn) {
    loginBtn.addEventListener('click', (e) => {
      e.preventDefault();
      openLogin();
    });
  }

  if (loginBackdrop) {
    loginBackdrop.addEventListener('click', closeLogin);
  }
  if (loginClose) {
    loginClose.addEventListener('click', closeLogin);
  }

  // Update footer dashboard visibility
  function updateFooterDashboardVisibility(signedIn) {
    const footerDashboard = document.querySelector('footer .footer-column a[href="dashboard.html"]');
    if (!footerDashboard) return;
    footerDashboard.style.display = signedIn ? 'inline-block' : 'none';
  }

  // UI updates after sign-in: build a small auth block on the right side
  function setSignedInUI() {
    const navAuth = document.querySelector('.nav-auth');
    if (!navAuth) {
      console.error('[AUTH] nav-auth element not found!');
      return;
    }

    // Build auth container
    navAuth.innerHTML = '';

    const dashboard = document.createElement('a');
    dashboard.className = 'btn btn-primary';
    dashboard.href = 'dashboard.html';
    dashboard.id = 'dashboardBtn';
    dashboard.textContent = 'Dashboard';
    
    debugLog('[AUTH] Creating dashboard button with href:', dashboard.href);
    
    // Add click handler to verify token before navigating
    dashboard.addEventListener('click', function(e) {
      const token = localStorage.getItem('access_token') || localStorage.getItem('aiCompanionToken');
      if (!token) {
        debugWarn('[AUTH] Dashboard clicked but no valid token found - preventing navigation');
        e.preventDefault();
        showToast('Session expired. Please sign in again.', 'error');
        renderSignedOutUI();
        updateFooterDashboardVisibility(false);
      }
    });

    const logoutBtn = document.createElement('button');
    logoutBtn.id = 'logoutBtnMain';
    logoutBtn.className = 'btn btn-outline';
    logoutBtn.textContent = 'Sign Out';
    logoutBtn.addEventListener('click', (e) => { e.preventDefault(); logout(); });

    navAuth.appendChild(dashboard);
    navAuth.appendChild(logoutBtn);
    
    debugLog('[AUTH] Dashboard button added to DOM:', document.getElementById('dashboardBtn'));

    // show footer dashboard link when signed in
    updateFooterDashboardVisibility(true);
  }

  async function initAuthUI() {
    const token = localStorage.getItem('access_token') || localStorage.getItem('aiCompanionToken');

    if (token) {
      setSignedInUI();
      updateFooterDashboardVisibility(true);
    } else {
      renderSignedOutUI();
      updateFooterDashboardVisibility(false);
    }
  }

  // Login submit handler
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      loginError.textContent = '';

      const email = document.getElementById('loginEmail').value.trim();
      const password = document.getElementById('loginPassword').value;

      if (!email || !password) {
        loginError.textContent = 'Email and password are required.';
        return;
      }

      const submitBtnLogin = document.getElementById('loginSubmit');
      submitBtnLogin.disabled = true;
      const originalLabelLogin = submitBtnLogin.textContent;
      submitBtnLogin.textContent = 'Signing in...';

      const loginUrl = `${config.api.baseURL}/api/auth/token`;

      try {
        // Send as form-encoded to match backend's expected parameters
        const form = new URLSearchParams();
        form.append('username', email);
        form.append('password', password);

        const res = await fetch(loginUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: form.toString(),
          credentials: 'include'
        });

        if (res.ok) {
          const data = await res.json();
          if (data && data.access_token) {
            localStorage.setItem('access_token', data.access_token);
            // compatibility shim
            localStorage.setItem('aiCompanionToken', data.access_token);
            if (data.user_id) localStorage.setItem('user_id', data.user_id);
            localStorage.setItem('user_name', data.username || data.email || email);
          }

          closeLogin();
          showToast('Signed in successfully', 'success');
          setSignedInUI();
          updateFooterDashboardVisibility(true);
        } else {
          const err = await res.json().catch(() => ({}));
          loginError.textContent = err.detail || err.error || 'Sign in failed';
        }
      } catch (err) {
        console.error('Login error', err);
        loginError.textContent = 'Network error. Try again.';
      } finally {
        submitBtnLogin.disabled = false;
        submitBtnLogin.textContent = originalLabelLogin;
      }
    });
  }

  // Initialize auth UI on load
  initAuthUI();

  // Re-check auth status when page becomes visible (user returns from another page)
  // This ensures home page reflects actual login state if user was logged out from dashboard
  document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
      debugLog('[AUTH] Page became visible - re-checking auth status');
      initAuthUI();
    }
  });

  // Also re-check on focus (user clicks back into window)
  window.addEventListener('focus', function() {
    debugLog('[AUTH] Window gained focus - re-checking auth status');
    initAuthUI();
  });

  // Logout implementation
  async function logout() {
    const API_BASE = config.api.baseURL;
    const logoutUrl = API_BASE ? `${API_BASE}/api/auth/logout` : `/api/auth/logout`;

    try {
      // best effort to notify server
      await fetch(logoutUrl, { method: 'POST', credentials: 'include' });
    } catch (err) {
      console.warn('Logout request failed', err);
    }

    // Clear local state
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_name');
    localStorage.removeItem('aiCompanionToken');
    localStorage.removeItem('dashboardSection'); // Also clear dashboard section preference

    // Update UI
    renderSignedOutUI();
    updateFooterDashboardVisibility(false);
    showToast('Signed out', 'success');
  }
});

// Global wrapper for openSignup to allow calling from onclick handlers
window.openSignup = function(event) {
  if (event) event.preventDefault();
  const signupModal = document.getElementById('signupModal');
  if (!signupModal) {
    // If signup modal doesn't exist (login page), redirect to home
    window.location.href = 'index.html';
    return;
  }
  signupModal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('modal-open');
  const firstInput = document.getElementById('signupUsername');
  if (firstInput) firstInput.focus();
};

// Global wrapper for login
window.openLogin = function(event) {
  if (event) event.preventDefault();
  const loginModal = document.getElementById('loginModal');
  if (!loginModal) {
    window.location.href = 'login.html';
    return;
  }
  loginModal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('modal-open');
  const firstInput = document.getElementById('email');
  if (firstInput) firstInput.focus();
};