# AI Companion Bot v3.1 MVP

A sophisticated AI companion chatbot platform with 5 unique personality archetypes, built with FastAPI and React.

## Features

- **5 Personality Archetypes**: Golden Retriever, Tsundere, Lawyer, Cool Girl, Toxic Ex
- **8-Step Quiz Funnel**: Personalized onboarding experience
- **Safety First**: Built-in distress detection, boundaries system, and consent management
- **Proactive Messaging**: Intelligent 7-gate system for timely interactions
- **Telegram Integration**: Deep linking to archetype-specific bots
- **Memory Management**: Weekly summarization and long-term context
- **Analytics**: Comprehensive tracking and insights
- **Tiered Access**: Free, Plus, and Premium subscription levels
- **Admin Panel**: Comprehensive dashboard for user management, analytics, and system monitoring

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Node.js 16+ (for frontend)
- OpenAI API key
- Telegram bot tokens

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
python reset_db.py

# Create admin user (optional)
python create_admin.py

# Start the backend
python run.py --all
```

Backend will run on `http://localhost:8010`

### Frontend Setup

```bash
cd frontend

# Serve frontend (using any static server)
python -m http.server 3000
```

Frontend will run on `http://localhost:3000`

## Project Structure

```
companion-bot/
├── backend/
│   ├── routers/          # API endpoints
│   ├── services/         # Business logic
│   ├── handlers/         # Message processing
│   ├── models/           # Data models
│   ├── jobs/             # Background tasks
│   ├── utils/            # Utilities
│   └── main.py           # FastAPI app
├── frontend/
│   ├── scripts/          # JavaScript modules
│   ├── styles/           # CSS files
│   └── *.html            # Pages
└── database/
    └── migrations/       # SQL migrations
```

## API Documentation

Visit `http://localhost:8010/api/docs` for interactive API documentation.

## Admin Panel

The admin panel is available at `http://localhost:3000/admin.html` for users with admin role.

### Admin Features

- **Dashboard**: Real-time statistics, user activity, and message analytics
- **User Management**: View, activate/deactivate users, upgrade tiers
- **Message Analytics**: Track message types, top users, and usage patterns
- **Archetype Distribution**: Visualize bot personality preferences
- **System Monitoring**: Check API health, database status, and performance

### Creating Admin Users

Use the backend script to create admin users:

```bash
cd backend
python create_admin.py <username> <email> <password>
```

Example:
```bash
python create_admin.py admin admin@companionai.com SecurePassword123!
```

The admin panel link appears automatically in the dashboard sidebar for admin users.

## Environment Variables

Key environment variables (see `.env.example`):

- `DATABASE_URL`: PostgreSQL connection string
- `LLM_API_KEY`: OpenAI API key
- `SECRET_KEY`: JWT secret
- `TELEGRAM_BOT_TOKEN`: Main bot token
- `TELEGRAM_BOT_*`: Archetype-specific bot usernames

## Testing

Run end-to-end tests:

```bash
./test_e2e.sh
```

## Architecture

- **Backend**: FastAPI, PostgreSQL, SQLAlchemy (async)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **AI**: OpenAI GPT-4
- **Messaging**: Telegram Bot API
- **Authentication**: JWT tokens

## Core Systems

1. **Quiz System**: 8-step onboarding with validation
2. **Boundary Manager**: Detects and enforces user boundaries
3. **Proactive Scheduler**: 7-gate system for intelligent messaging
4. **Context Builder**: Assembles conversation context with memory
5. **Mood Detector**: Identifies emotional states and distress
6. **Analytics**: Tracks events and generates insights

## License

Proprietary - All rights reserved

## Support

For issues or questions, contact the development team.
