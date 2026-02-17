# backend/main.py - Add security scheme
"""
FastAPI Backend Entry Point for AI Companion Bot v3.1
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import os
from dotenv import load_dotenv
import uvicorn

from utils.timezone import get_utc_now
from core.container import container

# Load environment variables
load_dotenv()

# Import routers
from routers import quiz, users, messages, admin, settings, boundaries, auth, chat_logs, bots
from database import engine, Base, get_db
from services.analytics import Analytics
from services.llm_client import OpenAILLMClient
from handlers.message_handler import MessageHandler
from handlers.command_handler import CommandHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting AI Companion Bot v3.1")
    
    try:
        # Create database tables (only if they don't exist)
        logger.info("Initializing database...")
        async with engine.begin() as conn:
            # Create all tables with current schema
            # Note: This only creates tables that don't exist - data is preserved
            logger.info("Creating tables if they don't exist...")
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
        await container.startup()
        logger.info("Backend initialized successfully")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Companion Bot")
    
    await container.shutdown()
    # Close database connections
    await engine.dispose()

# Create FastAPI app
app = FastAPI(
    title="AI Companion Bot API",
    description="Backend API for AI Companion Bot v3.1 MVP with OpenAI integration",
    version="3.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication and registration"
        },
        {
            "name": "Users",
            "description": "User management and profiles"
        },
        {
            "name": "Quiz",
            "description": "Personality quiz system"
        },
        {
            "name": "Messages",
            "description": "Messaging and chat endpoints"
        },
        {
            "name": "Settings",
            "description": "Bot settings and configuration"
        },
        {
            "name": "Boundaries",
            "description": "User boundary management"
        },
        {
            "name": "Admin",
            "description": "Administrative endpoints"
        },
    ]
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # "http://localhost:3000",
        # "http://localhost:8000",
        # "http://localhost:8008",
        # "http://localhost:8011",
        # "http://localhost:8010",
        # "https://bot.martofpk.com",
        # "https://www.bot.martofpk.com",
        # "https://martofpk.com",
        # "https://www.martofpk.com",
        "http://0.0.0.0:8001",
        # "https://0.0.0.0:8001",
            # "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get LLM client
async def get_llm_client():
    """Get LLM client."""
    try:
        return container.get_llm_client()
    except Exception:
        raise HTTPException(status_code=500, detail="LLM client not initialized")

# Dependency to get analytics service
async def get_analytics(db: AsyncSession = Depends(get_db)) -> Analytics:
    """Get analytics service."""
    return container.build_analytics(db)

# Dependency to get message handler
async def get_message_handler(
    db: AsyncSession = Depends(get_db),
    llm: OpenAILLMClient = Depends(get_llm_client),
    analytics: Analytics = Depends(get_analytics)
) -> MessageHandler:
    """Get message handler."""
    return container.build_message_handler(db)

# Dependency to get command handler
async def get_command_handler(
    db: AsyncSession = Depends(get_db),
    analytics: Analytics = Depends(get_analytics)
) -> CommandHandler:
    """Get command handler."""
    return container.build_command_handler(db)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(quiz.router, prefix="/api/quiz", tags=["Quiz"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(boundaries.router, prefix="/api/boundaries", tags=["Boundaries"])
app.include_router(chat_logs.router, prefix="/api/chat-logs", tags=["Chat Logs"])
app.include_router(bots.router, prefix="/api/bots", tags=["Bots"])

# Custom OpenAPI schema with security
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="AI Companion Bot API",
        version="3.1.0",
        description="Backend API for AI Companion Bot v3.1 MVP",
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/api/auth/token",
                    "scopes": {}
                }
            }
        }
    }
    
    # Add security to all endpoints except public ones
    for path in openapi_schema["paths"]:
        if not any(public_path in path for public_path in ["/auth/", "/health", "/test-openai", "/"]):
            for method in openapi_schema["paths"][path]:
                openapi_schema["paths"][path][method]["security"] = [{"OAuth2PasswordBearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "3.1.0",
        "timestamp": get_utc_now().isoformat(),
        "service": "ai-companion-bot",
        "openai_configured": container.is_ready
    }

# Test OpenAI endpoint
@app.get("/test-openai")
async def test_openai(
    prompt: str = "Hello, how are you?",
    llm: OpenAILLMClient = Depends(get_llm_client)
):
    """Test OpenAI integration."""
    try:
        response = await llm.client.chat.completions.create(
            model=llm.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        
        return {
            "success": True,
            "response": response.choices[0].message.content,
            "model": llm.model,
            "timestamp": get_utc_now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": get_utc_now().isoformat()
        }

# Root endpoint
@app.get("/")
async def read_root():
    """Root endpoint."""
    return {
        "message": "Welcome to AI Companion Bot v3.1 API with OpenAI",
        "docs": "/api/docs",
        "version": "3.1.0",
        "openai_model": container.get_llm_client().model if container.is_ready else "Not initialized"
    }

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", 8001)),
        reload=True,
        log_level="info"
    )