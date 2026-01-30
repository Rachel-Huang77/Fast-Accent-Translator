# app/core/db.py
"""
Database configuration and initialization module.
Handles Tortoise ORM setup, database connection, and migration configuration.
"""
import os
from tortoise import Tortoise
from dotenv import load_dotenv
from pathlib import Path

# Explicitly load .env from project root directory
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Database connection URL (PostgreSQL)
# Format: postgres://user:password@host:port/database
DB_URL = os.getenv("DATABASE_URL", "postgres://postgres:Postgre@127.0.0.1:5432/fat")

# Tortoise ORM configuration dictionary
# This configuration is also used by Aerich for database migrations
TORTOISE_ORM = {
    "connections": {"default": DB_URL},
    "apps": {
        "models": {
            "models": [
                "app.models.user",           # User model
                "app.models.conversation",   # Conversation model
                "app.models.transcript",     # Transcript model
                "app.models.license_key",    # License key model
                "aerich.models",             # Required: Let Aerich manage migration tables
            ],
            "default_connection": "default",
        },
    },
}

async def init_db():
    """
    Initialize Tortoise ORM database connection.
    
    This function should be called during application startup to establish
    the database connection and register all models.
    
    Note: Auto-generating schemas is disabled for production safety.
    Use Aerich migrations for schema management instead.
    """
    await Tortoise.init(config=TORTOISE_ORM)
    # Don't auto-generate tables in production; can use generate_schemas=True during development for quick start
    # await Tortoise.generate_schemas()

async def close_db():
    """
    Close all database connections.
    
    This function should be called during application shutdown to properly
    clean up database connections and resources.
    """
    await Tortoise.close_connections()
