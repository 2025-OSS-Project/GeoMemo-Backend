from fastapi import APIRouter, Depends, Query, HTTPException
from core.deps import get_current_user
from models.model import UserEntity
from schemas.user import DeleteUserResponse, NicknameUpdateRequest, NicknameUpdateResponse, PasswordUpdateRequest, PasswordUpdateResponse, UserProfileImageUpdate
from crud.user import delete_user, update_user_nickname, update_user_password
from db.database import get_db
from sqlalchemy.orm import Session
from enum import Enum

router = APIRouter(
    prefix="/api/user",
    tags=["user"]
)

class SearchType(str, Enum):
    nickname = "nickname"
    email = "email"

@router.post("/update-password", response_model=PasswordUpdateResponse)
def update_password(
    body: PasswordUpdateRequest,
    current_user: UserEntity = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    return update_user_password(session, current_user.user_id, body.password)


@router.post("/update-nickname", response_model=NicknameUpdateResponse)
def update_nickname(
    body: NicknameUpdateRequest,
    current_user: UserEntity = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    return update_user_nickname(session, current_user.user_id, body.nickname)

@router.delete("/delete-account", response_model=DeleteUserResponse)
def delete_account(
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return delete_user(current_user.user_id, db)

@router.post("/profile-image")
def update_profile_image(
    payload: UserProfileImageUpdate,
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    try:
        current_user.profile_image_url = payload.profile_image_url
        db.commit()
        db.refresh(current_user)
        return {
            "success": True,
            "error": None
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/search")
def search_users(
    keyword: str = Query(..., min_length=1),
    type: SearchType = Query(..., description="검색 타입: nickname 또는 email"),
    limit: int = Query(10, le=50, description="한 페이지당 결과 수"),
    offset: int = Query(0, description="건너뛸 유저 수"),
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)  # ✅ JWT 인증 필요
):
    try:
        query = db.query(UserEntity)

        if type == SearchType.nickname:
            query = query.filter(UserEntity.nickname.like(f"%{keyword}%"))
        elif type == SearchType.email:
            query = query.filter(UserEntity.email.like(f"%{keyword}%"))

        total = query.count()
        users = query.offset(offset).limit(limit).all()

        result = [
            {
                "userId": user.user_id,
                "username": user.email,
                "nickname": user.nickname,
                "profileImageUrl": user.profile_image_url
            }
            for user in users
        ]

        return {
            "success": True,
            "data": {
                "users": result,
                "total": total
            },
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }