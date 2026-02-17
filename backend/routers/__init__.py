# backend/routers/__init__.py
"""
Export all routers
"""
from .quiz import router as quiz_router
from .users import router as users_router
from .messages import router as messages_router
from .admin import router as admin_router
from .settings import router as settings_router
from .boundaries import router as boundaries_router
from .auth import router as auth_router  # Added this line

__all__ = [
    "quiz_router",
    "users_router", 
    "messages_router",
    "admin_router",
    "settings_router",
    "boundaries_router",
    "auth_router",  
]