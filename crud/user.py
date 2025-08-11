from sqlalchemy import func
from sqlalchemy.orm import Session
from models.model import UserEntity as User
from schemas.user import UserCreate, NicknameUpdateResponse, PasswordUpdateResponse, DeleteUserResponse
from core.security import hash_password, verify_password
from datetime import datetime
from models import model
from core.security import hash_password, verify_password  # verify_password 추가

def get_user_by_email(db: Session, email: str) -> User | None:
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

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


def update_user_password(db, user_id: int, password: str, new_password: str):
    # 사용자 조회
    user = db.query(model.UserEntity).filter(model.UserEntity.user_id == user_id).first()
    if not user:
        return PasswordUpdateResponse(
            success=False,
            data=None,
            error="사용자를 찾을 수 없습니다."
        )

    # 기존 비밀번호 검증
    if not verify_password(password, user.password):
        return PasswordUpdateResponse(
            success=False,
            data=None,
            error="기존 비밀번호가 일치하지 않습니다."
        )

    # 새 비밀번호 저장
    user.password = hash_password(new_password)
    user.updatedAt = datetime.now()
    db.commit()
    db.refresh(user)

    return PasswordUpdateResponse(
        success=True,
        data={
            "password": user.password,
            "updatedAt": user.updatedAt.isoformat()
        },
        error=None
    )


def update_user_nickname(db: Session, user_id: int, new_nickname: str) -> NicknameUpdateResponse:
    user = db.query(model.UserEntity).filter(model.UserEntity.user_id == user_id).first()
    if not user:
        return NicknameUpdateResponse(success=False, data=None, error="User not found")

    user.nickname = new_nickname
    user.updatedAt = datetime.now()
    db.commit()
    db.refresh(user)

    return NicknameUpdateResponse(
        success=True,
        data={
            "nickname": user.nickname,
            "updatedAt": user.updatedAt.isoformat()
        },
        error=None
    )

def delete_user(user_id: int, db: Session) -> DeleteUserResponse:
    user = db.query(model.UserEntity).filter(model.UserEntity.user_id == user_id).first()
    if not user:
        return DeleteUserResponse(success=False, data=None, error="User not found")
    
    db.delete(user)
    db.commit()

    return DeleteUserResponse(success=True, data={"userId": user_id}, error=None)

def get_user_details(db: Session, user_id:int):
    user = db.query(model.UserEntity).filter_by(user_id=user_id).first()
    # 팔로워 수 (나를 팔로우하는 사람 수)
    follower_count = db.query(func.count(model.FollowEntity.follower_id)) \
        .filter(model.FollowEntity.following_id == user_id) \
        .scalar()

    # 팔로잉 수 (내가 팔로우하는 사람 수)
    following_count = db.query(func.count(model.FollowEntity.following_id)) \
        .filter(model.FollowEntity.follower_id == user_id) \
        .scalar()
    return {
        "user_id": user.user_id,
        "user_profile": user.profile_image_url,
        "user_privacy": user.privacy_settings,
        "user_nickname": user.nickname,
        "follower_count": follower_count,
        "following_count": following_count
    }