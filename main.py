from typing import Union
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database_connection import get_db, engine
from database import Base
from auth import router as auth_router
from sms_api import router as sms_router
from profile_api import router as profile_router
import config

app = FastAPI(
    title="Fitora API",
    description="A fitness tracking API",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(sms_router)
app.include_router(profile_router)

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def read_root():
    return {"Hello": "World", "environment": config.ENVIRONMENT}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.get("/test-db")
async def test_database(db: AsyncSession = Depends(get_db)):
    result = await db.execute("SELECT 1")
    return {"database": "connected", "result": result.scalar()}