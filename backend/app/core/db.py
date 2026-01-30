# app/core/db.py
import os
from tortoise import Tortoise

# Database URL must be provided by environment (Render / Docker)
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL is not set")

TORTOISE_ORM = {
    "connections": {"default": DB_URL},
    "apps": {
        "models": {
            "models": [
                "app.models.user",
                "app.models.conversation",
                "app.models.transcript",
                "app.models.license_key",
                "aerich.models",
            ],
            "default_connection": "default",
        },
    },
}

async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)

    if os.getenv("ENV", "dev") != "prod":
        await Tortoise.generate_schemas()

async def close_db():
    await Tortoise.close_connections()
