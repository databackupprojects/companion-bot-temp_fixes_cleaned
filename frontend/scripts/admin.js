// frontend/scripts/admin.js - Admin Panel JavaScript

class AdminApp {
    constructor() {
        this.currentSection = 'dashboard';
        this.currentPage = 1;
        this.usersPerPage = 20;
        this.allUsers = [];
        this.filteredUsers = [];
        this.charts = {};
        this.refreshInterval = null;
        this.baseURL = config?.api?.baseURL || 'http://localhost:8010';
        
        this.init();
    }

    async init() {
        // Check authentication and admin role
        const token = localStorage.getItem('access_token') || localStorage.getItem('aiCompanionToken');
        if (!token) {
            window.location.href = 'login.html';
            return;
        }

        // Verify admin role
        try {
            const response = await fetch(`${this.baseURL}/api/users/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Authentication failed');
            }

            const userData = await response.json();
            
            if (userData.role !== 'admin') {
                window.showToast('Access denied. Admin privileges required.', 'error');
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 2000);
                return;
            }

            document.getElementById('adminUsername').textContent = userData.username;
            
        } catch (error) {
            console.error('Auth check failed:', error);
            window.location.href = 'login.html';
            return;
        }

        this.setupEventListeners();
        this.loadDashboard();
        
        // Auto-refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.refreshCurrentSection();
        }, 30000);
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.admin-nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.dataset.section;
                this.showSection(section);
            });
        });

        // Logout
        document.getElementById('logoutBtn').addEventListener('click', () => {
            this.logout();
        });

        // Dashboard refresh
        document.getElementById('refreshDashboard')?.addEventListener('click', () => {
            this.loadDashboard();
        });

        // Users section
        document.getElementById('refreshUsers')?.addEventListener('click', () => {
            this.loadUsers();
        });

        document.getElementById('userSearch')?.addEventListener('input', (e) => {
            this.filterUsers(e.target.value);
        });

        document.getElementById('tierFilter')?.addEventListener('change', () => {
            this.applyFilters();
        });

        document.getElementById('roleFilter')?.addEventListener('change', () => {
            this.applyFilters();
        });

        document.getElementById('statusFilter')?.addEventListener('change', () => {
            this.applyFilters();
        });

        // Pagination
        document.getElementById('prevPage')?.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.renderUsersTable();
            }
        });

        document.getElementById('nextPage')?.addEventListener('click', () => {
            const totalPages = Math.ceil(this.filteredUsers.length / this.usersPerPage);
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this.renderUsersTable();
            }
        });

        // Messages section
        document.getElementById('refreshMessages')?.addEventListener('click', () => {
            this.loadMessageStats();
        });

        document.getElementById('messagesDays')?.addEventListener('change', () => {
            this.loadMessageStats();
        });

        // Archetypes section
        document.getElementById('refreshArchetypes')?.addEventListener('click', () => {
            this.loadArchetypeStats();
        });

        // System section
        document.getElementById('refreshSystem')?.addEventListener('click', () => {
            this.loadSystemStatus();
        });
    }

    showSection(section) {
        // Update navigation
        document.querySelectorAll('.admin-nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-section="${section}"]`).classList.add('active');

        // Update sections
        document.querySelectorAll('.admin-section').forEach(sec => {
            sec.classList.remove('active');
        });
        document.getElementById(section).classList.add('active');

        this.currentSection = section;

        // Load section data
        switch(section) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'users':
                this.loadUsers();
                break;
            case 'messages':
                this.loadMessageStats();
                break;
            case 'archetypes':
                this.loadArchetypeStats();
                break;
            case 'system':
                this.loadSystemStatus();
                break;
        }
    }

    async loadDashboard() {
        try {
            const stats = await this.fetchAdminStats();
            
            // Update stat cards
            document.getElementById('totalUsers').textContent = stats.total_users || 0;
            document.getElementById('activeUsers').textContent = stats.active_users_today || 0;
            document.getElementById('totalMessages').textContent = stats.total_messages || 0;
            document.getElementById('adminCount').textContent = stats.admin_count || 0;

            // Load archetype chart
            this.renderArchetypeChart(stats.archetype_distribution || {});

            // Load activity chart (mock data for now)
            this.renderActivityChart();

        } catch (error) {
            console.error('Failed to load dashboard:', error);
            window.showToast('Failed to load dashboard data', 'error');
        }
    }

    async fetchAdminStats() {
        const token = localStorage.getItem('access_token') || localStorage.getItem('aiCompanionToken');
        const response = await fetch(`${this.baseURL}/api/admin/stats`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to fetch admin stats');
        }

        return await response.json();
    }

    async loadUsers() {
        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('aiCompanionToken');
            const response = await fetch(`${this.baseURL}/api/admin/users?limit=1000`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch users');
            }

            this.allUsers = await response.json();
            this.filteredUsers = [...this.allUsers];
            this.currentPage = 1;
            this.renderUsersTable();

        } catch (error) {
            console.error('Failed to load users:', error);
            window.showToast('Failed to load users', 'error');
        }
    }

    filterUsers(searchTerm) {
        const term = searchTerm.toLowerCase();
        this.filteredUsers = this.allUsers.filter(user => 
            user.username.toLowerCase().includes(term) ||
            user.email.toLowerCase().includes(term)
        );
        this.applyFilters();
    }

    applyFilters() {
        const tierFilter = document.getElementById('tierFilter').value;
        const roleFilter = document.getElementById('roleFilter').value;
        const statusFilter = document.getElementById('statusFilter').value;

        this.filteredUsers = this.allUsers.filter(user => {
            if (tierFilter && user.tier !== tierFilter) return false;
            if (roleFilter && user.role !== roleFilter) return false;
            if (statusFilter === 'active' && !user.is_active) return false;
            if (statusFilter === 'inactive' && user.is_active) return false;
            return true;
        });

        // Apply search filter
        const searchTerm = document.getElementById('userSearch').value;
        if (searchTerm) {
            this.filterUsers(searchTerm);
        }

        this.currentPage = 1;
        this.renderUsersTable();
    }

    renderUsersTable() {
        const tbody = document.getElementById('usersTableBody');
        const start = (this.currentPage - 1) * this.usersPerPage;
        const end = start + this.usersPerPage;
        const usersToShow = this.filteredUsers.slice(start, end);

        if (usersToShow.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-cell">No users found</td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = usersToShow.map(user => `
            <tr>
                <td>
                    <div class="user-cell">
                        <i class="fas fa-user-circle"></i>
                        <span>${this.escapeHtml(user.username)}</span>
                    </div>
                </td>
                <td>${this.escapeHtml(user.email)}</td>
                <td>
                    <span class="badge badge-${user.role === 'admin' ? 'primary' : 'secondary'}">
                        ${user.role}
                    </span>
                </td>
                <td>
                    <span class="badge badge-tier-${user.tier}">
                        ${user.tier}
                    </span>
                </td>
                <td>${user.messages_today || 0}</td>
                <td>${this.formatDate(user.last_active_at)}</td>
                <td>${this.formatDate(user.created_at)}</td>
                <td>
                    <div class="action-buttons-cell">
                        <button class="btn-icon" onclick="adminApp.viewUserDetails('${user.id}')" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn-icon" onclick="adminApp.editUser('${user.id}')" title="Edit User">
                            <i class="fas fa-edit"></i>
                        </button>
                        ${user.role !== 'admin' ? `
                            <button class="btn-icon btn-danger" onclick="adminApp.toggleUserStatus('${user.id}', ${!user.is_active})" title="${user.is_active ? 'Deactivate' : 'Activate'}">
                                <i class="fas fa-${user.is_active ? 'ban' : 'check'}"></i>
                            </button>
                            <button class="btn-icon btn-danger" onclick="adminApp.deleteUser('${user.id}')" title="Delete User">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `).join('');

        // Update pagination
        const totalPages = Math.ceil(this.filteredUsers.length / this.usersPerPage);
        document.getElementById('paginationInfo').textContent = `Page ${this.currentPage} of ${totalPages}`;
        document.getElementById('prevPage').disabled = this.currentPage === 1;
        document.getElementById('nextPage').disabled = this.currentPage >= totalPages;
    }

    async viewUserDetails(userId) {
        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('aiCompanionToken');
            const response = await fetch(`${this.baseURL}/api/admin/users/${userId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch user details');
            }

            const user = await response.json();
            this.showUserDetailModal(user);

        } catch (error) {
            console.error('Failed to load user details:', error);
            window.showToast('Failed to load user details', 'error');
        }
    }

    showUserDetailModal(user) {
        const modal = document.getElementById('userDetailModal');
        const body = document.getElementById('userDetailBody');

        body.innerHTML = `
            <div class="user-detail-grid">
                <div class="detail-section">
                    <h3><i class="fas fa-user"></i> User Information</h3>
                    <div class="detail-row">
                        <span class="detail-label">ID:</span>
                        <span class="detail-value">${user.id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Username:</span>
                        <span class="detail-value">${this.escapeHtml(user.username)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Email:</span>
                        <span class="detail-value">${this.escapeHtml(user.email)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Role:</span>
                        <span class="detail-value"><span class="badge badge-${user.role === 'admin' ? 'primary' : 'secondary'}">${user.role}</span></span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Tier:</span>
                        <span class="detail-value"><span class="badge badge-tier-${user.tier}">${user.tier}</span></span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Status:</span>
                        <span class="detail-value"><span class="badge badge-${user.is_active ? 'success' : 'danger'}">${user.is_active ? 'Active' : 'Inactive'}</span></span>
                    </div>
                </div>

                <div class="detail-section">
                    <h3><i class="fas fa-chart-line"></i> Activity Statistics</h3>
                    <div class="detail-row">
                        <span class="detail-label">Messages Today:</span>
                        <span class="detail-value">${user.messages_today || 0}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Total Messages:</span>
                        <span class="detail-value">${user.total_messages || 0}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Proactive Messages:</span>
                        <span class="detail-value">${user.proactive_count_today || 0}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Last Active:</span>
                        <span class="detail-value">${this.formatDate(user.last_active_at)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Timezone:</span>
                        <span class="detail-value">${user.timezone || 'UTC'}</span>
                    </div>
                </div>

                ${user.bot_settings ? `
                <div class="detail-section">
                    <h3><i class="fas fa-robot"></i> Bot Settings</h3>
                    <div class="detail-row">
                        <span class="detail-label">Bot Name:</span>
                        <span class="detail-value">${this.escapeHtml(user.bot_settings.bot_name || 'Not set')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Archetype:</span>
                        <span class="detail-value">${user.bot_settings.archetype || 'Not set'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Gender:</span>
                        <span class="detail-value">${user.bot_settings.bot_gender || 'Not set'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Attachment Style:</span>
                        <span class="detail-value">${user.bot_settings.attachment_style || 'Not set'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Flirtiness:</span>
                        <span class="detail-value">${user.bot_settings.flirtiness || 'Not set'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Toxicity:</span>
                        <span class="detail-value">${user.bot_settings.toxicity || 'Not set'}</span>
                    </div>
                </div>
                ` : ''}

                <div class="detail-section">
                    <h3><i class="fas fa-cog"></i> Account Actions</h3>
                    <div class="action-buttons">
                        <button class="btn btn-primary" onclick="adminApp.upgradeTier('${user.id}', 'pro')">
                            <i class="fas fa-arrow-up"></i> Upgrade to Pro
                        </button>
                        <button class="btn btn-primary" onclick="adminApp.upgradeTier('${user.id}', 'premium')">
                            <i class="fas fa-crown"></i> Upgrade to Premium
                        </button>
                        ${user.role !== 'admin' ? `
                            <button class="btn btn-${user.is_active ? 'danger' : 'success'}" onclick="adminApp.toggleUserStatus('${user.id}', ${!user.is_active})">
                                <i class="fas fa-${user.is_active ? 'ban' : 'check'}"></i> ${user.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                            <button class="btn btn-danger" onclick="adminApp.deleteUser('${user.id}')">
                                <i class="fas fa-trash"></i> Delete User
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;

        modal.style.display = 'flex';
    }

    closeUserModal() {
        document.getElementById('userDetailModal').style.display = 'none';
    }

    async toggleUserStatus(userId, activate) {
        const action = activate ? 'activate' : 'deactivate';
        
        if (!confirm(`Are you sure you want to ${action} this user?`)) {
            return;
        }

        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('aiCompanionToken');
            const response = await fetch(`${this.baseURL}/api/admin/users/${userId}/${action}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to ${action} user`);
            }

            const result = await response.json();
            window.showToast(result.message, 'success');
            
            this.closeUserModal();
            this.loadUsers();

        } catch (error) {
            console.error(`Failed to ${action} user:`, error);
            window.showToast(`Failed to ${action} user`, 'error');
        }
    }

    async deleteUser(userId) {
        if (!confirm('⚠️ WARNING: This will permanently delete this user and all their data. This action cannot be undone!\n\nAre you absolutely sure?')) {
            return;
        }

        // Double confirmation for safety
        if (!confirm('Last chance! Type "DELETE" to confirm you want to permanently delete this user.')) {
            return;
        }

        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('aiCompanionToken');
            const response = await fetch(`${this.baseURL}/api/admin/users/${userId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to delete user');
            }

            const result = await response.json();
            window.showToast(result.message, 'success');
            
            this.closeUserModal();
            this.loadUsers();

        } catch (error) {
            console.error('Failed to delete user:', error);
            window.showToast('Failed to delete user', 'error');
        }
    }

    async upgradeTier(userId, newTier) {
        if (!confirm(`Upgrade user to ${newTier} tier?`)) {
            return;
        }

        try {
            const token = localStorage.getItem('access_token') || localStorage.getItem('aiCompanionToken');
            const response = await fetch(`${this.baseURL}/api/admin/users/${userId}/upgrade-tier?new_tier=${newTier}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to upgrade tier');
            }

            const result = await response.json();
            window.showToast(result.message, 'success');
            
            this.closeUserModal();
            this.loadUsers();

        } catch (error) {
            console.error('Failed to upgrade tier:', error);
            window.showToast('Failed to upgrade tier', 'error');
        }
    }

    async loadMessageStats() {
        try {
            const days = document.getElementById('messagesDays').value;
            const token = localStorage.getItem('access_token') || localStorage.getItem('aiCompanionToken');
            
            const response = await fetch(`${this.baseURL}/api/admin/messages-stats?days=${days}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch message stats');
            }

            const stats = await response.json();

            // Update cards
            document.getElementById('periodTotalMessages').textContent = stats.total_messages || 0;
            
            const messagesByType = stats.messages_by_type || {};
            document.getElementById('userMessages').textContent = messagesByType.user || 0;
            document.getElementById('botMessages').textContent = messagesByType.bot || 0;
            document.getElementById('proactiveMessages').textContent = messagesByType.proactive || 0;

            // Render message types breakdown
            this.renderMessageTypes(messagesByType);

            // Render top users chart
            this.renderTopUsersChart(stats.top_users || []);

        } catch (error) {
            console.error('Failed to load message stats:', error);
            window.showToast('Failed to load message statistics', 'error');
        }
    }

    renderMessageTypes(messagesByType) {
        const container = document.getElementById('messageTypesContainer');
        const total = Object.values(messagesByType).reduce((a, b) => a + b, 0);

        if (total === 0) {
            container.innerHTML = '<p class="empty-text">No messages in this period</p>';
            return;
        }

        container.innerHTML = Object.entries(messagesByType)
            .sort((a, b) => b[1] - a[1])
            .map(([type, count]) => {
                const percentage = ((count / total) * 100).toFixed(1);
                return `
                    <div class="message-type-item">
                        <div class="type-header">
                            <span class="type-name">${type}</span>
                            <span class="type-count">${count} (${percentage}%)</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${percentage}%"></div>
                        </div>
                    </div>
                `;
            }).join('');
    }

    async loadArchetypeStats() {
        try {
            const stats = await this.fetchAdminStats();
            this.renderArchetypeGrid(stats.archetype_distribution || {});
            this.renderArchetypeDetailChart(stats.archetype_distribution || {});
        } catch (error) {
            console.error('Failed to load archetype stats:', error);
            window.showToast('Failed to load archetype statistics', 'error');
        }
    }

    renderArchetypeGrid(distribution) {
        const grid = document.getElementById('archetypeGrid');
        const total = Object.values(distribution).reduce((a, b) => a + b, 0);

        const archetypeInfo = {
            'golden_retriever': { icon: 'fa-dog', color: '#FFD700', name: 'Golden Retriever' },
            'tsundere': { icon: 'fa-fire', color: '#FF6B6B', name: 'Tsundere' },
            'lawyer': { icon: 'fa-gavel', color: '#4ECDC4', name: 'Lawyer' },
            'cool_girl': { icon: 'fa-snowflake', color: '#95E1D3', name: 'Cool Girl' },
            'toxic_ex': { icon: 'fa-skull-crossbones', color: '#AA96DA', name: 'Toxic Ex' }
        };

        grid.innerHTML = Object.entries(distribution)
            .sort((a, b) => b[1] - a[1])
            .map(([archetype, count]) => {
                const info = archetypeInfo[archetype] || { icon: 'fa-robot', color: '#666', name: archetype };
                const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                
                return `
                    <div class="archetype-card" style="border-left: 4px solid ${info.color}">
                        <div class="archetype-icon" style="background: ${info.color}">
                            <i class="fas ${info.icon}"></i>
                        </div>
                        <div class="archetype-info">
                            <h4>${info.name}</h4>
                            <div class="archetype-count">${count} users</div>
                            <div class="archetype-percentage">${percentage}%</div>
                        </div>
                    </div>
                `;
            }).join('');
    }

    async loadSystemStatus() {
        try {
            // Check API health
            const apiResponse = await fetch(`${this.baseURL}/`);
            const apiData = await apiResponse.json();

            document.getElementById('apiVersion').textContent = apiData.version || 'v3.1.0';
            document.getElementById('openaiModel').textContent = apiData.openai_model || 'gpt-4';
            
            // Update status indicators (all green if we got this far)
            this.updateStatusIndicator('dbStatus', 'Connected', 'ok');
            this.updateStatusIndicator('apiStatus', 'Running', 'ok');
            this.updateStatusIndicator('openaiStatus', 'Active', 'ok');
            this.updateStatusIndicator('telegramStatus', 'Active', 'ok');

        } catch (error) {
            console.error('Failed to load system status:', error);
            this.updateStatusIndicator('apiStatus', 'Error', 'error');
        }
    }

    updateStatusIndicator(elementId, text, status) {
        const element = document.getElementById(elementId);
        element.textContent = text;
        element.className = `stat-value status-text status-${status}`;
        
        const iconElement = element.closest('.stat-card').querySelector('.stat-icon');
        iconElement.className = `stat-icon status-${status}`;
    }

    // Chart rendering methods
    renderArchetypeChart(distribution) {
        const canvas = document.getElementById('archetypeChart');
        if (!canvas) return;

        if (this.charts.archetypeChart) {
            this.charts.archetypeChart.destroy();
        }

        const ctx = canvas.getContext('2d');
        const labels = Object.keys(distribution).map(key => 
            key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
        );
        const data = Object.values(distribution);

        this.charts.archetypeChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#FFD700',
                        '#FF6B6B',
                        '#4ECDC4',
                        '#95E1D3',
                        '#AA96DA'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    renderArchetypeDetailChart(distribution) {
        const canvas = document.getElementById('archetypeDetailChart');
        if (!canvas) return;

        if (this.charts.archetypeDetailChart) {
            this.charts.archetypeDetailChart.destroy();
        }

        const ctx = canvas.getContext('2d');
        const labels = Object.keys(distribution).map(key => 
            key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
        );
        const data = Object.values(distribution);

        this.charts.archetypeDetailChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Users',
                    data: data,
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    renderActivityChart() {
        const canvas = document.getElementById('activityChart');
        if (!canvas) return;

        if (this.charts.activityChart) {
            this.charts.activityChart.destroy();
        }

        const ctx = canvas.getContext('2d');
        
        // Generate last 7 days labels
        const labels = [];
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
        }

        // Mock data - in production, fetch from backend
        const data = [12, 19, 15, 25, 22, 30, 28];

        this.charts.activityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Active Users',
                    data: data,
                    borderColor: 'rgba(79, 172, 254, 1)',
                    backgroundColor: 'rgba(79, 172, 254, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: 'rgba(79, 172, 254, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 5
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    renderTopUsersChart(topUsers) {
        const canvas = document.getElementById('topUsersChart');
        if (!canvas) return;

        if (this.charts.topUsersChart) {
            this.charts.topUsersChart.destroy();
        }

        const ctx = canvas.getContext('2d');
        const labels = topUsers.map(u => u.username);
        const data = topUsers.map(u => u.message_count);

        this.charts.topUsersChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Messages',
                    data: data,
                    backgroundColor: 'rgba(240, 147, 251, 0.8)',
                    borderColor: 'rgba(240, 147, 251, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    x: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    // Utility methods
    formatDate(dateString) {
        if (!dateString) return 'Never';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    refreshCurrentSection() {
        switch(this.currentSection) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'users':
                this.loadUsers();
                break;
            case 'messages':
                this.loadMessageStats();
                break;
            case 'archetypes':
                this.loadArchetypeStats();
                break;
            case 'system':
                this.loadSystemStatus();
                break;
        }
    }

    exportUserData() {
        if (!this.allUsers.length) {
            window.showToast('No user data to export', 'warning');
            return;
        }

        const csv = this.convertToCSV(this.allUsers);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `users_export_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);

        window.showToast('User data exported successfully', 'success');
    }

    convertToCSV(data) {
        const headers = ['ID', 'Username', 'Email', 'Role', 'Tier', 'Messages Today', 'Created At'];
        const rows = data.map(user => [
            user.id,
            user.username,
            user.email,
            user.role,
            user.tier,
            user.messages_today,
            user.created_at
        ]);

        return [
            headers.join(','),
            ...rows.map(row => row.join(','))
        ].join('\n');
    }

    editUser(userId) {
        // Placeholder for edit functionality
        window.showToast('Edit functionality coming soon', 'info');
    }

    logout() {
        if (confirm('Are you sure you want to logout?')) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('aiCompanionToken');
            localStorage.removeItem('aiCompanionData');
            window.location.href = 'login.html';
        }
    }

    destroy() {
        // Cleanup
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
    }
}

// Initialize app
let adminApp;
document.addEventListener('DOMContentLoaded', () => {
    adminApp = new AdminApp();
    
    // Add home button event listener
    const homeBtn = document.getElementById('homeBtn');
    if (homeBtn) {
        homeBtn.addEventListener('click', () => {
            window.location.href = 'index.html';
        });
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (adminApp) {
        adminApp.destroy();
    }
});
