from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.router import router
from core.config import SETTINGS
from core.logging import setup_logging
from db.session import create_db_engine

setup_logging(log_level=SETTINGS.logging.log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database engine...")
    app.state.engine = create_db_engine()
    logger.info("Database engine created")

    yield

    logger.info("Disposing database engine...")
    app.state.engine.dispose()
    logger.info("Database engine disposed")


app = FastAPI(
    debug=SETTINGS.logging.log_level == "DEBUG",
    lifespan=lifespan,
    root_path=SETTINGS.server.root_path,
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)


if __name__ == "__main__":
    logger.info("Starting application...")
    logger.info(f"Using settings: {SETTINGS}")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_config=None,
    )
