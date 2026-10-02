from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.database import init_db
from app.api import evaluation, providers, tasks
from app.models import evaluation_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация приложения"""
    # При старте
    await init_db()
    yield
    # При остановке (очистка ресурсов если нужна)


app = FastAPI(
    title=settings.APP_NAME,
    description="Универсальный инструмент для тестирования промтов и моделей LLM",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic's default input/context can echo a submitted URL containing secrets.
    errors = [{key: item[key] for key in ('type', 'loc', 'msg') if key in item} for item in exc.errors()]
    return JSONResponse(status_code=422, content={'detail': errors})


# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(evaluation.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "name": settings.APP_NAME,
        "description": "LLM Prompt & Model Testing Tool",
        "docs_url": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {"status": "healthy"}
