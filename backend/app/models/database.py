from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(f"sqlite:///{settings.DATABASE_PATH}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # ONVIF, USB, RTSP
    address = Column(String, nullable=True)  # IP or URL
    port = Column(Integer, nullable=True)
    username = Column(String, nullable=True)  # encrypted
    password = Column(String, nullable=True)  # encrypted
    rtsp_url = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    zones = relationship("Zone", back_populates="camera", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="camera", cascade="all, delete-orphan")


class Zone(Base):
    __tablename__ = "zones"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, ForeignKey("cameras.id"), nullable=False)
    name = Column(String, nullable=False)
    polygon = Column(JSON, nullable=False)  # Array of {x, y} points
    enabled = Column(Boolean, default=True)
    
    camera = relationship("Camera", back_populates="zones")


class Event(Base):
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, ForeignKey("cameras.id"), nullable=False)
    type = Column(String, nullable=False)  # person_detected, person_left, motion
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    clip_path = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    
    camera = relationship("Camera", back_populates="events")


# Create tables
Base.metadata.create_all(bind=engine)
