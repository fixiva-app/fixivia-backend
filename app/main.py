from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.dev import router as dev_router
from app.api.bookings import router as bookings_router
from app.api.catalog import router as catalog_router
from app.api.health import router as health_router
from app.api.me import router as me_router
from app.api.partners import router as partners_router
from app.api.technicians import router as tech_router
from app.config import settings
from app.db import SessionLocal, init_db
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if settings.seed_on_start:
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()
    yield


app = FastAPI(title="Fixvia API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(dev_router)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(partners_router)
app.include_router(catalog_router)
app.include_router(bookings_router)
app.include_router(tech_router)
app.include_router(analytics_router)
