from typing import Union
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database_connection import get_db, engine
from database import Base
from auth import router as auth_router
from sms_api import router as sms_router
from profile_api import router as profile_router
from minio_api import router as image_router
import config
from contextlib import asynccontextmanager

app = FastAPI(
    title="Fitora API",
    description="A fitness tracking API",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(sms_router)
app.include_router(profile_router)
app.include_router(image_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield


@app.get("/")
async def read_root():
    return {"Hello": "World", "environment": config.ENVIRONMENT}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)