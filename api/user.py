from fastapi import APIRouter, Depends
from core.deps import get_current_user
from models.model import UserEntity
from schemas.user import DeleteUserResponse, NicknameUpdateRequest, NicknameUpdateResponse, PasswordUpdateRequest, PasswordUpdateResponse
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
