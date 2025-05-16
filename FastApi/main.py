import os
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, select
DB_NAME = os.getenv("DB_NAME", "movie")
DB_USERNAME = os.getenv("DB_USERNAME", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "12345")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# # SSL setup
# ssl_context = (cafile="./certs/server.crt")
# ssl_context.check_hostname = False

# DATABASE_URL = f"postgresql+asyncpg://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
DATABASE_URL = f"postgresql+asyncpg://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, )
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Title(Base):
    __tablename__ = "title_basics"

    tconst: Mapped[str] = mapped_column(String, primary_key=True)
    titletype: Mapped[str] = mapped_column(String)
    primarytitle: Mapped[str] = mapped_column(String)
    originaltitle: Mapped[str] = mapped_column(String)
    isadult: Mapped[int] = mapped_column(Integer)
    startyear: Mapped[int] = mapped_column(Integer)
    endyear: Mapped[int] = mapped_column(Integer)
    runtimeminutes: Mapped[int] = mapped_column(Integer)
    genres: Mapped[str] = mapped_column(String)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/api/v1/movies")
async def get_movies(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Title).where(Title.titletype == "movie").limit(20))
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/v1/tvseries")
async def get_tvseries(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Title).where(Title.titletype == "tvSeries").limit(20))
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/v1/tvminiseries")
async def get_tvminiseries(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Title).where(Title.titletype == "tvMiniSeries").limit(20))
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/v1/movies/{title}")
async def search_movies(title: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Title).where(Title.titletype == "movie", Title.primarytitle.ilike(f"%{title}%")))
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/v1/tvseries/{title}")
async def search_tvseries(title: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Title).where(Title.titletype == "tvSeries", Title.primarytitle.ilike(f"%{title}%")))
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/v1/tvminiseries/{title}")
async def search_tvminiseries(title: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Title).where(Title.titletype == "tvMiniSeries", Title.primarytitle.ilike(f"%{title}%")))
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
