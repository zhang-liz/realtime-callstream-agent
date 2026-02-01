"""Voice Agent FastAPI application."""

import uvicorn

from fastapi import FastAPI

from config import Config
from state import CallStateManager
from exceptions import ConfigurationError
from core.logging import configure_logging, get_logger
from routers.voice import router as voice_router, get_config
from routers.media import router as media_router

# Configure structured logging before any other app code
configure_logging()
logger = get_logger()

# Load configuration
try:
    config = Config.from_env()
except ValueError as e:
    logger.error("Configuration error", error=str(e))
    raise ConfigurationError(f"Failed to load configuration: {e}") from e

# Initialize call state manager
call_state_manager = CallStateManager(config)

app = FastAPI(title="Voice Agent", version="1.0.0")

# Dependency override: inject config for routes
app.dependency_overrides[get_config] = lambda: config

# Attach call state manager for WebSocket handler
app.state.call_state_manager = call_state_manager

# Mount routers
app.include_router(voice_router)
app.include_router(media_router)


@app.get("/")
async def root() -> dict:
    """Health and API info."""
    return {"message": "Voice Agent API", "status": "running"}


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=config.host,
        port=config.port,
        reload=True,
        log_level="info",
    )
