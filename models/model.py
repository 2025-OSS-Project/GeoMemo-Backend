from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    DateTime, ForeignKey, Double
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base


class UserEntity(Base):
    __tablename__ = "UserEntity"

    user_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    email = Column(String(100), nullable=True)
    password = Column(String(256), nullable=True)
    name = Column(String(10), nullable=True)
    nickname = Column(String(10), nullable=True)
    phone = Column(String(11), nullable=True)
    profile_image_url = Column(String(512), nullable=True)
    privacy_settings = Column(String(10), nullable=False, default="open")  # "open", "semi", "closed"
    view_settings = Column(String(10), nullable=False, default="all")  # "all" | "follows" | "self"

    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    memos = relationship("MemoEntity", back_populates="user")
    memo_scraps = relationship("MemoScrapEntity", back_populates="user")
    insights = relationship("InsightEntity", back_populates="user")
    email_verifies = relationship("EmailVerifyEntity", back_populates="user")
    followers = relationship("FollowEntity", foreign_keys="[FollowEntity.following_id]", back_populates="following")
    followings = relationship("FollowEntity", foreign_keys="[FollowEntity.follower_id]", back_populates="follower")


class EmotionEntity(Base):
    __tablename__ = "EmotionEntity"

    emotion_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    emotion_score = Column(Float, nullable=True)
    emotion_label = Column(String(10), nullable=True)
    memo_id = Column(Integer, ForeignKey("MemoEntity.memo_id"), nullable=False)

    memo = relationship("MemoEntity", back_populates="emotions")


class LocationEntity(Base):
    __tablename__ = "LocationEntity"

    location_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(20), nullable=True)
    latitude = Column(Double, nullable=True)
    longitude = Column(Double, nullable=True)
    address = Column(String(40), nullable=True)
    category = Column(String(30), nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())

    memos = relationship("MemoEntity", back_populates="location")


class MemoScrapEntity(Base):
    __tablename__ = "MemoScrapEntity"

    scrap_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("UserEntity.user_id"), nullable=False)
    memo_id = Column(Integer, ForeignKey("MemoEntity.memo_id"), nullable=False)

    user = relationship("UserEntity", back_populates="memo_scraps")
    memo = relationship("MemoEntity", back_populates="memo_scraps")


class InsightEntity(Base):
    __tablename__ = "InsightEntity"

    insight_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    emotion_avg = Column(Float, nullable=True)
    user_id = Column(Integer, ForeignKey("UserEntity.user_id"), nullable=False)
    content = Column(Text, nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserEntity", back_populates="insights")


class MemoEntity(Base):
    __tablename__ = "MemoEntity"

    memo_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    content = Column(Text, nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_public = Column(Boolean, nullable=True)
    user_id = Column(Integer, ForeignKey("UserEntity.user_id"), nullable=False)
    location_id = Column(Integer, ForeignKey("LocationEntity.location_id"), nullable=False)

    user = relationship("UserEntity", back_populates="memos")
    location = relationship("LocationEntity", back_populates="memos")
    emotions = relationship("EmotionEntity", back_populates="memo")
    memo_scraps = relationship("MemoScrapEntity", back_populates="memo")
    photos = relationship("PhotoEntity", back_populates="memo")


class PhotoEntity(Base):
    __tablename__ = "PhotoEntity"

    photo_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    photo_url = Column(String(255), nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    memo_id = Column(Integer, ForeignKey("MemoEntity.memo_id"), nullable=False)

    memo = relationship("MemoEntity", back_populates="photos")


class EmailVerifyEntity(Base):
    __tablename__ = "EmailVerifyEntity"

    verify_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("UserEntity.user_id"), nullable=False)
    verification_code = Column(Integer, nullable=True)
    is_verified = Column(Boolean, nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("UserEntity", back_populates="email_verifies")


class FollowEntity(Base):
    __tablename__ = "FollowEntity"

    follower_id = Column(Integer, ForeignKey("UserEntity.user_id"), primary_key=True)
    following_id = Column(Integer, ForeignKey("UserEntity.user_id"), primary_key=True)
    is_approved = Column(Boolean, nullable=False, default=False)

    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    follower = relationship("UserEntity", foreign_keys=[follower_id], back_populates="followings")
    following = relationship("UserEntity", foreign_keys=[following_id], back_populates="followers")