from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .bootstrap import seed_roles
from .config import get_settings
from .database import Base, engine, ensure_schema
from .routers.admin import router as admin_router
from .routers.admin_documents import router as admin_documents_router
from .routers.auth import router as auth_router
from .routers.batches import router as batches_router
from .routers.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    seed_roles()
    settings.uploads_path.mkdir(parents=True, exist_ok=True)
    yield


settings = get_settings()

app = FastAPI(title=settings.project_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(batches_router)
app.include_router(documents_router)
app.include_router(admin_router)
app.include_router(admin_documents_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": settings.version}