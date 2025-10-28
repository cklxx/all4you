"""
Database configuration and session management
"""

from sqlalchemy import create_engine, Column, String, DateTime, Integer, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from core.config import Settings

settings = Settings()

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Database models
class TrainingTask(Base):
    """Training task model"""
    __tablename__ = "training_tasks"

    id = Column(String, primary_key=True)
    name = Column(String, index=True)
    model_name = Column(String)
    data_file = Column(String)
    config_file = Column(String)
    status = Column(String, default="pending")  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Training metrics
    total_steps = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)
    current_loss = Column(Float, nullable=True)
    best_loss = Column(Float, nullable=True)

    # Configuration
    config = Column(JSON)

    # Output
    output_dir = Column(String, nullable=True)
    log_file = Column(String, nullable=True)


class DataFile(Base):
    """Data file model"""
    __tablename__ = "data_files"

    id = Column(String, primary_key=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    file_type = Column(String)  # json, jsonl, csv, txt
    format_type = Column(String)  # alpaca, sharegpt, raw

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    total_samples = Column(Integer, default=0)
    file_size = Column(Integer)  # in bytes
    metadata_json = Column("metadata", JSON)


class TrainingConfig(Base):
    """Training configuration template"""
    __tablename__ = "training_configs"

    id = Column(String, primary_key=True)
    name = Column(String, index=True, unique=True)
    description = Column(String)

    model_name = Column(String)
    training_method = Column(String)  # sft, lora, qlora, dpo, grpo

    config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_default = Column(Integer, default=0)


def init_db():
    """Initialize database"""
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Dependency for FastAPI
def get_db():
    """FastAPI dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
