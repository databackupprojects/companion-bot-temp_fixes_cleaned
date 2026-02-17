# AI Companion Bot v3.1 - Backend

AI Companion Bot with OpenAI integration, featuring 5 archetypes, personality customization, and intelligent conversation.

## Features

- **5 Personality Archetypes**: Golden Retriever, Tsundere, Lawyer, Cool Girl, Toxic Ex
- **OpenAI GPT-4 Integration**: Powered by OpenAI's most advanced models
- **Telegram Bot Integration**: Seamless messaging experience
- **7-Gate Proactive System**: Intelligent, context-aware proactive messaging
- **User Boundaries & Safety**: Robust safety features including distress detection
- **Memory Management**: Long-term memory and conversation summarization
- **Rate Limiting & Tier System**: Free, Plus, and Premium tiers with message limits
- **Analytics Dashboard**: Comprehensive event tracking and metrics
- **Docker Support**: Easy deployment with Docker Compose

## Quick Start

### Prerequisites

- **Python 3.11+** (3.11 or higher recommended)
- **PostgreSQL 15+** (for production) or SQLite (for development)
- **Redis 7+** (for Celery task queue)
- **OpenAI API Key** (with GPT-4 access)
- **Telegram Bot Token** (from @BotFather)

### Installation

1. **Clone the repository** (or create from this codebase):
```bash
git clone <repository-url>
cd ai-companion-bot
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
# You'll need to set:
# - LLM_API_KEY (your OpenAI API key)
# - TELEGRAM_BOT_TOKEN (your Telegram bot token)
# - DATABASE_URL (PostgreSQL connection string)
# - REDIS_URL (Redis connection string)
```

4. **Initialize the database**:
```bash
# Initialize database tables
python -c "from backend.database import init_db; import asyncio; asyncio.run(init_db())"
```

5. **Run the application**:
```bash
# Option 1: Run API server only
python backend/run.py --api

# Option 2: Run Telegram bot only
python backend/run.py --telegram

# Option 3: Run all services (API + Telegram + Background jobs)
python backend/run.py --all

# Option 4: Run specific services
python backend/run.py --api --telegram
```

### Using Docker (Recommended)

1. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key and Telegram bot token
```

2. **Start all services**:
```bash
docker-compose up -d
```

3. **View logs**:
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f telegram-bot
```

4. **Stop services**:
```bash
docker-compose down
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | Yes | `postgresql://postgres:123123@localhost:5432/companion_bot` |
| `REDIS_URL` | Redis connection URL | Yes | `redis://localhost:6379/0` |
| `LLM_API_KEY` | OpenAI API Key | Yes | - |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | Yes | - |
| `SECRET_KEY` | JWT Secret Key | No | Randomly generated |
| `ENVIRONMENT` | Environment (development/production) | No | `development` |
| `API_PORT` | API server port | No | `8001` |
| `OPENAI_MODEL` | OpenAI model to use | No | `gpt-4` |
| `LOG_LEVEL` | Logging level | No | `INFO` |

### Database Setup

#### PostgreSQL (Production)
```sql
CREATE DATABASE companion_bot;
CREATE USER companion_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE companion_bot TO companion_user;
```

#### SQLite (Development)
```bash
# In .env file:
DATABASE_URL=sqlite+aiosqlite:///./companion_bot.db
```

## API Documentation

Once the server is running, you can access:

- **Interactive API Docs**: http://localhost:8001/api/docs
- **ReDoc Documentation**: http://localhost:8001/api/redoc
- **Health Check**: http://localhost:8001/health
- **OpenAI Test**: http://localhost:8001/test-openai?prompt=Hello

## API Endpoints

### Quiz System (`/api/quiz/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/start` | Start a new quiz session |
| POST | `/step/{step_number}` | Submit quiz step |
| POST | `/complete` | Complete quiz and get Telegram token |
| GET | `/config/{token}` | Get quiz configuration |
| POST | `/quick-start` | Quick start with predefined archetype |

### User Management (`/api/users/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/me` | Get current user information |
| GET | `/settings` | Get bot settings |
| PUT | `/settings` | Update bot settings |
| GET | `/limits` | Get user message limits |
| POST | `/consent` | Update spice consent |

### Messaging (`/api/messages/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/send` | Send message to bot |
| GET | `/history` | Get message history |
| DELETE | `/clear` | Clear message history |
| POST | `/support` | Trigger support mode |
| WebSocket | `/ws/{user_id}` | Real-time chat WebSocket |

### Boundaries (`/api/boundaries/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get all boundaries for user |
| POST | `/` | Create new boundary |
| DELETE | `/{boundary_id}` | Delete boundary |
| POST | `/space-retract` | Retract space boundary |

### Settings (`/api/settings/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get bot settings |
| PUT | `/` | Update bot settings |
| GET | `/advanced` | Get advanced settings |
| PUT | `/advanced` | Update advanced settings |

### Admin (`/api/admin/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats` | Get admin statistics |
| GET | `/users` | Get all users |
| GET | `/support-requests` | Get support requests |

## Telegram Bot

### Getting a Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Start a chat and send `/newbot`
3. Follow the prompts to create your bot
4. Copy the bot token provided
5. Add it to your `.env` file as `TELEGRAM_BOT_TOKEN`

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Start or restart conversation |
| `/support` | Get real help (drops character) |
| `/settings` | View personality settings |
| `/personality` | View personality description |
| `/forget [topic]` | Set topic boundary |
| `/boundaries` | View all boundaries |
| `/reset [type]` | Reset conversation/personality |
| `/help` | Show all commands |

### Setting Webhook (for production)

```bash
curl -F "url=https://your-domain.com/webhook/telegram" \
     https://api.telegram.org/bot{YOUR_BOT_TOKEN}/setWebhook
```

## Archetypes

### 1. Golden Retriever 🐕‍🦺
**Personality**: Excited, loyal, always supportive
**Example**: "HEY!!! 😊😊 oh man I was literally just thinking about you!!"

### 2. Tsundere 😤→😊
**Personality**: Acts annoyed but cares deeply
**Example**: "...oh. you're back. whatever. it's not like i was waiting."

### 3. Lawyer ⚖️
**Personality**: Argumentative, intellectual, playful
**Example**: "Objection. That's hearsay and you know it."

### 4. Cool Girl 😎
**Personality**: Unbothered, independent, effortlessly cool
**Example**: "hey. thought about texting you. so I did."

### 5. Toxic Ex 🔥
**Personality**: Hot and cold, dramatic, chaotic
**Example**: "oh so NOW you text me. cool cool cool. whatever."

## Safety Features

### 1. Support Mode
Type `/support` at any time to drop all persona and get genuine help. The bot will respond with crisis resources and offer real conversation.

### 2. Distress Detection
Automatically detects phrases indicating genuine distress:
- "I'm really not okay"
- "I can't do this anymore"
- Self-harm language
- "I'm serious" / "this is real"

### 3. Boundaries System
Users can set boundaries that the bot will never violate:
- **Topic boundaries**: "Don't talk about work"
- **Timing boundaries**: "No morning messages"
- **Behavior boundaries**: "Give me space"
- **Frequency boundaries**: "Too many messages"

### 4. 24-Hour Hard Stop
If a user says "leave me alone" or "stop messaging me", the bot will pause proactive messages for 24 hours.

### 5. Consent Required
"Toxic Ex" archetype and "spicy" toxicity levels require explicit user consent.

## Rate Limiting

### User Tiers
| Tier | Messages/Day | Proactive/Day | Price |
|------|-------------|---------------|-------|
| Free | 20 | 1 | $0 |
| Plus | 200 | 3 | $9.99/month |
| Premium | 1000 | 5 | $19.99/month |

### System Limits
- **Rate Limit**: 20 messages per minute per user
- **Deduplication**: 5-second window for duplicate messages
- **Max Message Length**: 4000 characters

## Memory System

### Short-term Memory
- Last 50 messages kept in active context
- Recent mood tracking (last 5 messages)
- Pending question tracking

### Long-term Memory
- Weekly summarization of old conversations
- Fact extraction using OpenAI
- Categorized memory (preferences, life events, relationships)
- Importance scoring (1-5 scale)

## Background Jobs

| Job | Interval | Description |
|-----|----------|-------------|
| Daily Reset | 5 minutes | Resets daily message counters per user timezone |
| Memory Summarization | 6 hours | Summarizes old conversations into long-term memory |
| Data Cleanup | 1 hour | Cleans up old mood history, logs, and expired data |
| Proactive Scheduler | 15 minutes | Sends proactive messages to eligible users |

## Development

### Project Structure
```
backend/
├── config.py              # Configuration constants
├── database.py            # Database connection
├── main.py               # FastAPI application entry point
├── run.py                # Application runner
├── models/
│   ├── models.py         # Pydantic models
│   └── sql_models.py     # SQLAlchemy ORM models
├── routers/              # API endpoint routers
├── services/             # Business logic services
│   ├── llm_client.py     # OpenAI integration
│   ├── context_builder.py # LLM context construction
│   ├── boundary_manager.py # Boundary detection
│   ├── proactive_scheduler.py # Proactive messaging
│   └── analytics.py      # Event tracking
├── handlers/             # Message and command handlers
├── jobs/                 # Background jobs
├── utils/                # Utility functions
├── tasks/                # Celery tasks
└── telegram_bot.py       # Telegram bot integration
```

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v
```

### Code Formatting
```bash
# Install formatting tools
pip install black isort flake8

# Format code
black backend/
isort backend/

# Check code style
flake8 backend/
```

### Database Migrations
```bash
# Install Alembic
pip install alembic

# Initialize Alembic (first time)
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "Add new feature"

# Apply migration
alembic upgrade head
```

## Deployment

### Production Checklist
- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Use strong, unique `SECRET_KEY`
- [ ] Enable HTTPS with SSL certificates
- [ ] Configure proper logging (file rotation, log levels)
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure PostgreSQL backups
- [ ] Set up firewall rules (allow only necessary ports)
- [ ] Configure error tracking (Sentry)
- [ ] Set up rate limiting at infrastructure level
- [ ] Configure alerting for critical issues

### Deployment Options

#### Option 1: Docker Compose (Simplest)
```bash
# Production docker-compose.prod.yml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: companion_bot
  
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
  
  backend:
    image: your-registry/companion-bot:latest
    ports:
      - "8001:8001"
    environment:
      ENVIRONMENT: production
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@postgres/companion_bot
      REDIS_URL: redis://redis:6379/0
      LLM_API_KEY: ${LLM_API_KEY}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
    depends_on:
      - postgres
      - redis
```

#### Option 2: Kubernetes
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: companion-bot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: companion-bot
  template:
    metadata:
      labels:
        app: companion-bot
    spec:
      containers:
      - name: backend
        image: your-registry/companion-bot:latest
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: companion-secrets
              key: database-url
        - name: LLM_API_KEY
          valueFrom:
            secretKeyRef:
              name: companion-secrets
              key: openai-api-key
```

#### Option 3: Serverless (AWS Lambda)
```yaml
# serverless.yml
service: companion-bot

provider:
  name: aws
  runtime: python3.11
  region: us-east-1

functions:
  api:
    handler: backend.main.app
    events:
      - httpApi: '*'
  telegram:
    handler: backend.telegram_bot.webhook_handler
    events:
      - httpApi:
          path: /webhook/telegram
          method: post
```

## Monitoring & Logging

### Health Endpoints
- `GET /health` - Application health status
- `GET /health/db` - Database connection check
- `GET /health/redis` - Redis connection check
- `GET /health/openai` - OpenAI API status

### Logging Configuration
```python
# In config.py
LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'companion_bot.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'default',
        },
    },
    'loggers': {
        'backend': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
        },
    },
}
```

### Metrics (Prometheus)
```python
# Install: pip install prometheus-client
from prometheus_client import Counter, Histogram

# Define metrics
MESSAGES_RECEIVED = Counter('messages_received_total', 'Total messages received')
MESSAGES_SENT = Counter('messages_sent_total', 'Total messages sent')
RESPONSE_TIME = Histogram('response_time_seconds', 'Response time in seconds')
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check DATABASE_URL in .env
   - Ensure PostgreSQL is running: `pg_isready`
   - Verify credentials and permissions

2. **OpenAI API Errors**
   - Verify LLM_API_KEY is set
   - Check OpenAI account balance
   - Ensure model access (GPT-4 requires special access)

3. **Telegram Bot Not Responding**
   - Verify TELEGRAM_BOT_TOKEN
   - Check if webhook is set correctly
   - Ensure bot has message permissions

4. **Redis Connection Issues**
   - Check REDIS_URL in .env
   - Ensure Redis server is running
   - Verify firewall rules allow connections

5. **Rate Limiting Issues**
   - Check user tier limits
   - Verify rate limit configuration
   - Check for duplicate messages

### Debug Mode
```bash
# Set debug logging
LOG_LEVEL=DEBUG

# Enable SQL logging
SQL_ECHO=true

# Run with debug
python backend/run.py --all --debug
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend tests/

# Run specific test file
pytest tests/test_messages.py -v
```

---

**AI Companion Bot v3.1** - Making AI companionship accessible, safe, and engaging.

*Built with ❤️ and OpenAI GPT-4*
