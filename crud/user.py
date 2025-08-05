from sqlalchemy.orm import Session
from models.model import UserEntity as User
from schemas.user import UserCreate
from core.security import hash_password, verify_password
from datetime import datetime
from typing import Optional

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        email=user.email,
        password=hash_password(user.password),
        name=user.name,
        nickname=user.nickname,
        phone=user.phone,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user

def update_user_password(db: Session, user_id: int, new_password: str) -> Optional[User]:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None
    user.password = hash_password(new_password)
    user.updatedAt = datetime.now()
    db.commit()
    db.refresh(user)
    return user

def update_user_nickname(db: Session, user_id: int, new_nickname: str) -> Optional[User]:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None
    user.nickname = new_nickname
    user.updatedAt = datetime.now()
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True
