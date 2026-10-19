import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import engine, Base
from app.routers import accounts, videos, posts, cron, auth
from app.services.scheduler import start_scheduler, shutdown_scheduler

# Crear tablas en SQLite automáticamente si no existen
Base.metadata.create_all(bind=engine)

# Asegurar carpeta de subidas
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arrancar el motor en segundo plano
    start_scheduler()
    yield
    # Detener limpiamente al apagar el servidor
    shutdown_scheduler()

app = FastAPI(
    title="Metricool Personal API",
    description="Backend para gestión multi-cuenta, personalización y programación automática de videos en YouTube, Instagram y TikTok.",
    version="1.0.0",
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de rutas de la API
app.include_router(accounts.router)
app.include_router(videos.router)
app.include_router(posts.router)
app.include_router(cron.router)
app.include_router(auth.router)

from fastapi.responses import FileResponse

# Servir archivos estáticos del frontend si existen
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "app": "Metricool Personal API",
        "status": "online",
        "docs_url": "/docs",
        "cron_trigger_url": "/api/cron/trigger"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
