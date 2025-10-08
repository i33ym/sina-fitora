from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, Text, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database_connection import Base

class UserBase(BaseModel):
    email: str
    phone: Optional[str] = None
    verified: Optional[bool] = False
    google_id: Optional[str] = None
    fcm_token: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    current_height: Optional[Decimal] = None
    current_weight: Optional[Decimal] = None
    target_height: Optional[Decimal] = None
    target_weight: Optional[Decimal] = None
    main_purpose: Optional[str] = None
    target_date: Optional[date] = None
    activeness_level: Optional[str] = None
    motivation: Optional[str] = None
    preferred_diet: Optional[str] = None
    diet_restrictions: Optional[List[str]] = None
    version: Optional[int] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class CodeBase(BaseModel):
    code: str
    session: str
    expires_at: Optional[datetime] = None

class CodeCreate(CodeBase):
    pass

class Code(CodeBase):
    issued_at: datetime

    class Config:
        from_attributes = True

class TrackingBase(BaseModel):
    user_id: int
    details: Optional[dict] = None

class TrackingCreate(TrackingBase):
    pass

class Tracking(TrackingBase):
    id: int
    logged_at: datetime

    class Config:
        from_attributes = True

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    google_id = Column(String, unique=True, nullable=True, index=True)
    fcm_token = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    current_height = Column(Numeric(5, 2), nullable=True)
    current_weight = Column(Numeric(5, 2), nullable=True)
    target_height = Column(Numeric(5, 2), nullable=True)
    target_weight = Column(Numeric(5, 2), nullable=True)
    main_purpose = Column(String, nullable=True)
    target_date = Column(Date, nullable=True)
    activeness_level = Column(String, nullable=True)
    motivation = Column(Text, nullable=True)
    preferred_diet = Column(String, nullable=True)
    diet_restrictions = Column(ARRAY(String), nullable=True)
    version = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    trackings = relationship("TrackingModel", back_populates="user")

class CodeModel(Base):
    __tablename__ = "codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False)
    session = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    issued_at = Column(DateTime, default=datetime.utcnow)

class TrackingModel(Base):
    __tablename__ = "trackings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    details = Column(Text, nullable=True)
    logged_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserModel", back_populates="trackings")