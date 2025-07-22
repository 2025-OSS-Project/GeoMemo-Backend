from sqlalchemy import (
    Column, BigInteger, String, Float, Text, Boolean,
    DateTime, ForeignKey, Double
)
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime


class UserEntity(Base):
    __tablename__ = "UserEntity"

    user_id = Column(BigInteger, primary_key=True, index=True)
    email = Column(String(20), nullable=True)
    password = Column(String(20), nullable=True)
    name = Column(String(10), nullable=True)
    nickname = Column(String(10), nullable=True)
    phone = Column(String(11), nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memos = relationship("MemoEntity", back_populates="user")
    memo_scraps = relationship("MemoScrapEntity", back_populates="user")
    insights = relationship("InsightEntity", back_populates="user")
    email_verifies = relationship("EmailVerifyEntity", back_populates="user")


class EmotionEntity(Base):
    __tablename__ = "EmotionEntity"

    emotion_id = Column(BigInteger, primary_key=True, index=True)
    emotion_score = Column(Float, nullable=True)
    emotion_label = Column(String(10), nullable=True)
    memo_id = Column(BigInteger, ForeignKey("MemoEntity.memo_id"), nullable=False)

    memo = relationship("MemoEntity", back_populates="emotions")


class LocationEntity(Base):
    __tablename__ = "LocationEntity"

    location_id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(20), nullable=True)
    latitude = Column(Double, nullable=True)
    longitude = Column(Double, nullable=True)
    address = Column(String(40), nullable=True)
    category = Column(String(30), nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)

    memos = relationship("MemoEntity", back_populates="location")


class MemoScrapEntity(Base):
    __tablename__ = "MemoScrapEntity"

    scrap_id = Column(BigInteger, primary_key=True, index=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    user_id = Column(BigInteger, ForeignKey("UserEntity.user_id"), nullable=False)
    memo_id = Column(BigInteger, ForeignKey("MemoEntity.memo_id"), nullable=False)

    user = relationship("UserEntity", back_populates="memo_scraps")
    memo = relationship("MemoEntity", back_populates="memo_scraps")


class InsightEntity(Base):
    __tablename__ = "InsightEntity"

    insight_id = Column(BigInteger, primary_key=True, index=True)
    emotion_avg = Column(Float, nullable=True)
    user_id = Column(BigInteger, ForeignKey("UserEntity.user_id"), nullable=False)
    content = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserEntity", back_populates="insights")


class MemoEntity(Base):
    __tablename__ = "MemoEntity"

    memo_id = Column(BigInteger, primary_key=True, index=True)
    content = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_public = Column(Boolean, nullable=True)
    user_id = Column(BigInteger, ForeignKey("UserEntity.user_id"), nullable=False)
    location_id = Column(BigInteger, ForeignKey("LocationEntity.location_id"), nullable=False)

    user = relationship("UserEntity", back_populates="memos")
    location = relationship("LocationEntity", back_populates="memos")
    emotions = relationship("EmotionEntity", back_populates="memo")
    memo_scraps = relationship("MemoScrapEntity", back_populates="memo")
    photos = relationship("PhotoEntity", back_populates="memo")


class PhotoEntity(Base):
    __tablename__ = "PhotoEntity"

    photo_id = Column(BigInteger, primary_key=True, index=True)
    photo_url = Column(String(255), nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    memo_id = Column(BigInteger, ForeignKey("MemoEntity.memo_id"), nullable=False)

    memo = relationship("MemoEntity", back_populates="photos")


class EmailVerifyEntity(Base):
    __tablename__ = "EmailVerifyEntity"

    verify_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("UserEntity.user_id"), nullable=False)
    verification_code = Column(BigInteger, nullable=True)
    is_verified = Column(Boolean, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)

    user = relationship("UserEntity", back_populates="email_verifies")
