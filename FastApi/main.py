# app/main.py
import os
import ssl
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, select, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

APP_PORT = int(os.getenv("APP_PORT", 3000))
HOST = os.getenv("HOST", "0.0.0.0")
DB_NAME = os.getenv("DB_NAME", "movie")
DB_USERNAME = os.getenv("DB_USERNAME", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "12345")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("uvicorn")

# Load SSL certificate
# ssl_cert_path = './certs/server.crt'
# ssl_context = ssl.create_default_context(cafile=ssl_cert_path)

# DATABASE_URL = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
DATABASE_URL = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require", "sslrootcert": ssl_cert_path})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Title(Base):
    __tablename__ = "title_basics"

    tconst = Column(String, primary_key=True, index=True)
    titletype = Column(String)
    primarytitle = Column(String)
    originaltitle = Column(String)
    isadult = Column(Integer)
    startyear = Column(Integer)
    endyear = Column(Integer)
    runtimeminutes = Column(Integer)
    genres = Column(Text)

app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/v1/{media_type}")
def get_media_list(media_type: str, db=SessionLocal()):
    try:
        stmt = select(Title).where(Title.titletype == media_type).limit(20)
        result = db.execute(stmt).scalars().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/v1/{media_type}/{title}")
def search_media_by_title(media_type: str, title: str, db=SessionLocal()):
    try:
        stmt = select(Title).where(
            Title.primarytitle.ilike(f"%{title}%"),
            Title.titletype == media_type
        )
        result = db.execute(stmt).scalars().all()
        return result
    except SQLAlchemyError as e:d
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
