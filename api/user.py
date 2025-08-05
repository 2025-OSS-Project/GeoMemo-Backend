from fastapi import APIRouter, Depends, HTTPException
from core.deps import get_current_user
from models.model import UserEntity
from schemas.user import (
    UserDeleteResponse,
    NicknameUpdateRequest, NicknameUpdateResponse,
    PasswordUpdateRequest, PasswordUpdateResponse
)
from schemas.response import APIResponse
from crud.user import delete_user, update_user_nickname, update_user_password
from db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/api/user",
    tags=["user"]
)

@router.post("/update-password", response_model=PasswordUpdateResponse)
def update_password(
    body: PasswordUpdateRequest,
    current_user: UserEntity = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    user = update_user_password(session, current_user.user_id, body.password)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return APIResponse(success=True, data={
        "password": user.password,
        "updatedAt": user.updatedAt.isoformat()
    })


@router.post("/update-nickname", response_model=NicknameUpdateResponse)
def update_nickname(
    body: NicknameUpdateRequest,
    current_user: UserEntity = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    user = update_user_nickname(session, current_user.user_id, body.nickname)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return APIResponse(success=True, data={
        "nickname": user.nickname,
        "updatedAt": user.updatedAt.isoformat()
    })


@router.post("/delete-account", response_model=UserDeleteResponse)
def delete_account(
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = delete_user(db, current_user.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return APIResponse(success=True, data={"userId": current_user.user_id})
