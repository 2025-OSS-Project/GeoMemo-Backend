import re
from sqlalchemy import func
from sqlalchemy.orm import Session
from exception.exception import ErrorCode, OperatedException
from models.model import UserEntity as User
from schemas.user import UserCreate, NicknameUpdateResponse, PasswordUpdateResponse, DeleteUserResponse
from core.security import hash_password, verify_password
from datetime import datetime
from models import model
from core.security import hash_password, verify_password  # verify_password 추가

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate) -> User:
    
    # 3. 비밀번호 형식 체크 (예: 8자 이상, 숫자/문자 포함)
    if len(user.password) < 8 or not re.search(r"[A-Za-z]", user.password) or not re.search(r"\d", user.password):
        raise OperatedException(
            status_code=400,
            error_code=ErrorCode.USR_003,
            detail="비밀번호 형식이 올바르지 않습니다. (최소 8자, 문자+숫자 포함)"
        )

    # 4. 닉네임 길이 체크 (예: 최대 20자)
    if len(user.nickname) > 20:
        raise OperatedException(
            status_code=400,
            error_code=ErrorCode.USR_006,
            detail="닉네임 길이가 너무 깁니다. (최대 20자)"
        )

    # 5. 전화번호 형식 체크 (숫자만, 10~11자리)
    if not re.fullmatch(r"\d{10,11}", user.phone):
        raise OperatedException(
            status_code=400,
            error_code=ErrorCode.USR_007,
            detail="전화번호 형식이 올바르지 않습니다."
        )

    # 6. 닉네임 중복 체크
    existing_nickname = db.query(User).filter(User.nickname == user.nickname).first()
    if existing_nickname:
        raise OperatedException(
            status_code=409,
            error_code=ErrorCode.USR_004,
            detail="이미 존재하는 사용자명입니다."
        )

    # 7. 이메일 중복 체크
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise OperatedException(
            status_code=409,
            error_code=ErrorCode.USR_005,
            detail="이미 사용 중인 이메일입니다."
        )

    # 8. 사용자 생성
    db_user = User(
        email=user.email,
        password=hash_password(user.password),
        name=user.name,
        nickname=user.nickname,
        phone=user.phone,
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except Exception as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.USR_999,
            detail=f"서버 내부 오류: {str(e)}"
        )

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
    user = db.query(model.UserEntity).filter(model.UserEntity.user_id==user_id).first()
    if not user:
        return None  # 또는 예외 발생
    return {
        "user_id": user.user_id,
        "user_profile": user.profile_image_url,
        "user_privacy": user.privacy_settings,
        "user_nickname": user.nickname,
        "follower_count": user.follower_count,
        "following_count": user.following_count
    }
