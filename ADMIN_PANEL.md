# Admin Panel Documentation

## Overview

The AI Companion Bot Admin Panel provides comprehensive tools for system administration, user management, and analytics monitoring.

## Access

**URL**: `http://localhost:3000/admin.html`

**Requirements**: 
- Valid authentication token
- Admin role assigned to user account

## Features

### 1. Dashboard Overview

Real-time statistics and insights:

- **Total Users**: Count of all registered users
- **Active Users Today**: Users who were active in the last 24 hours
- **Total Messages**: Cumulative message count across all users
- **Admin Accounts**: Number of admin users in the system

#### Charts
- **Archetype Distribution**: Pie chart showing bot personality preferences
- **User Activity**: 7-day line chart of active users

#### Quick Actions
- Export user data to CSV
- Navigate to message analytics
- Check system health

### 2. User Management

Comprehensive user administration interface:

#### User Table
- **Columns**: Username, Email, Role, Tier, Messages, Last Active, Created Date
- **Pagination**: 20 users per page
- **Search**: Filter users by username or email
- **Filters**: 
  - Tier (Free, Pro, Premium)
  - Role (User, Admin)
  - Status (Active, Inactive)

#### User Actions
- **View Details**: See complete user profile and bot settings
- **Edit User**: Modify user information
- **Activate/Deactivate**: Toggle user account status
- **Upgrade Tier**: Change subscription level (Free → Pro → Premium)

#### User Detail Modal
Shows comprehensive user information:
- Basic info (ID, username, email, role, tier, status)
- Activity stats (messages today, total messages, proactive messages)
- Bot settings (name, archetype, gender, attachment style, flirtiness, toxicity)
- Account actions (upgrade tier, activate/deactivate)

### 3. Message Analytics

Track messaging patterns and user engagement:

#### Statistics
- **Total Messages**: Count for selected period
- **User Messages**: Messages sent by users
- **Bot Messages**: AI-generated responses
- **Proactive Messages**: System-initiated conversations

#### Period Selection
- Last 7 days
- Last 14 days
- Last 30 days
- Last 90 days

#### Visualizations
- **Top 10 Active Users**: Horizontal bar chart
- **Message Type Breakdown**: Progress bars showing distribution

### 4. Archetype Distribution

Analyze bot personality preferences:

#### Archetype Cards
Visual representation of each archetype:
- Golden Retriever
- Tsundere
- Lawyer
- Cool Girl
- Toxic Ex

Each card shows:
- User count
- Percentage of total
- Archetype-specific icon and color

#### Detailed Analysis
Bar chart comparing all archetypes

### 5. System Status

Monitor system health and performance:

#### Status Indicators
- **Database**: Connection status
- **API Server**: Running status
- **OpenAI**: Integration status
- **Telegram Bot**: Bot status

#### API Information
- Version number
- OpenAI model in use
- System uptime

#### Performance Metrics
- Average response time
- Requests today
- Error rate

## Admin Endpoints

### GET /admin/stats
Returns dashboard statistics

**Response**:
```json
{
  "total_users": 150,
  "active_users_today": 45,
  "total_messages": 3420,
  "admin_count": 3,
  "archetype_distribution": {
    "golden_retriever": 45,
    "tsundere": 32,
    "lawyer": 28,
    "cool_girl": 25,
    "toxic_ex": 20
  }
}
```

### GET /admin/users
List all users with pagination

**Parameters**:
- `limit` (default: 100): Users per page
- `offset` (default: 0): Pagination offset

### GET /admin/users/{user_id}
Get detailed user information

**Response includes**:
- User profile
- Message statistics
- Bot settings
- Activity timestamps

### POST /admin/users/{user_id}/activate
Activate a deactivated user account

### POST /admin/users/{user_id}/deactivate
Deactivate a user account (cannot deactivate admins)

### POST /admin/users/{user_id}/upgrade-tier
Upgrade user subscription tier

**Parameters**:
- `new_tier`: One of ["free", "pro", "premium"]

**Response**:
```json
{
  "message": "User tier upgraded from free to pro",
  "user_id": "uuid",
  "new_tier": "pro",
  "expires_at": "2025-02-01T00:00:00"
}
```

### GET /admin/messages-stats
Get message analytics for specified period

**Parameters**:
- `days` (default: 7): Number of days to analyze

**Response**:
```json
{
  "period_days": 7,
  "total_messages": 850,
  "messages_by_type": {
    "user": 425,
    "bot": 400,
    "proactive": 25
  },
  "top_users": [
    {"username": "john_doe", "message_count": 120},
    {"username": "jane_smith", "message_count": 95}
  ]
}
```

## Security

### Authentication
- All admin endpoints require valid JWT token
- Token must be included in `Authorization` header as `Bearer <token>`

### Authorization
- User must have `role = "admin"` in database
- Regular users attempting admin access receive 403 Forbidden
- Admin panel automatically redirects non-admin users to dashboard

### Admin Creation
Admins can only be created through backend script:

```bash
cd backend
python create_admin.py <username> <email> <password>
```

## UI/UX Features

### Auto-Refresh
- Dashboard auto-refreshes every 30 seconds
- Manual refresh buttons on all sections

### Responsive Design
- Mobile-friendly sidebar
- Collapsible navigation
- Adaptive charts and tables

### Visual Feedback
- Toast notifications for actions
- Loading states for async operations
- Hover effects and animations
- Color-coded badges (role, tier, status)

### Data Export
- Export user list to CSV
- Download includes key fields for analysis

## Chart Library

Uses **Chart.js 4.4.0** for visualizations:
- Doughnut charts for distributions
- Line charts for time series
- Bar charts for comparisons

## Styling

Custom admin panel styles in `frontend/styles/admin.css`:
- Gradient backgrounds
- Card-based layout
- Professional color scheme
- Smooth transitions and animations

## Best Practices

### User Management
1. Always verify user details before deactivation
2. Use tier upgrades for customer support
3. Monitor inactive admins regularly
4. Export user data for backups

### Analytics
1. Check message stats weekly
2. Monitor archetype distribution for trends
3. Identify top users for engagement
4. Track system performance metrics

### System Monitoring
1. Regular health checks
2. Monitor error rates
3. Check database connectivity
4. Verify Telegram integration

## Troubleshooting

### Admin Panel Not Loading
- Check if backend is running on port 8010
- Verify user has admin role in database
- Clear browser cache and cookies
- Check browser console for errors

### Charts Not Displaying
- Ensure Chart.js CDN is accessible
- Check for JavaScript errors in console
- Verify API endpoints return valid data

### User Actions Failing
- Confirm JWT token is valid
- Check admin permissions
- Verify target user exists
- Review backend logs for errors

## Future Enhancements

Potential additions for future versions:
- Real-time WebSocket updates
- Advanced analytics with date range filters
- Bulk user operations
- Email notification system
- Custom report generation
- System configuration interface
- API key management
- Rate limit configuration
- Database backup/restore UI

## Support

For issues or feature requests related to the admin panel:
1. Check API documentation at `/api/docs`
2. Review backend logs in `backend/companion_bot.log`
3. Inspect browser developer console
4. Contact system administrator
