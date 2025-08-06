from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.deps import get_current_user
from schemas.memo import CreateMemoRequest, LocationSchema, MemoSchema, UpdateMemoRequest, UserSchema
from schemas.response import APIResponse
from crud.memo import create_memo, delete_memo, update_memo_with_photos
from db.database import get_db


router = APIRouter(prefix="/api/memo", tags=["Memo"])

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Optional

@router.post("/")
async def create_memo_api(
    memo_create : CreateMemoRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    location_data = {
        "name": memo_create.location_name,
        "latitude": memo_create.location_latitude,
        "longitude": memo_create.location_longitude,
        "address": memo_create.location_address,
        "category": memo_create.location_category,
    }

    memo = create_memo(
        db=db,
        user_id=current_user.user_id,
        memo_create = memo_create
    )

    memo = MemoSchema(
        memoId=memo.memo_id,
        content=memo.content,
        createdAt=memo.createdAt,
        updatedAt=memo.updatedAt,
        isPublic=memo.is_public,
        fileUrl=[photo.photo_url for photo in memo.photos],
        location=LocationSchema(
            name=memo_create.location_name,
            latitude= memo_create.location_latitude,
            longitude= memo_create.location_longitude,
            address= memo_create.location_address,
            category= memo_create.location_category,
        ),
        user=UserSchema(
            userId=memo.user.user_id,
            username=memo.user.nickname,
            photoUrl=memo.user.profile_image_url
        )
    )

    return APIResponse[MemoSchema](success=True, data=memo)


@router.post("/delete/{memo_id}")
def delete_memo_api(memo_id: int, db: Session = Depends(get_db)):
    result = delete_memo(db, memo_id)
    return APIResponse(success=True, data=memo_id, error=None)

@router.post("/update")
async def update_memo_api(
    memo_update: UpdateMemoRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # 메모 수정
    memo = update_memo_with_photos(
        db=db,
        user_id=current_user.user_id,
        memo_update=memo_update
    )

    # 응답 데이터 구성
    response_data = MemoSchema(
        memoId=memo.memo_id,
        content=memo.content,
        createdAt=memo.createdAt,
        updatedAt=memo.updatedAt,
        isPublic=memo.is_public,
        fileUrl=[photo.photo_url for photo in memo.photos],
        location=LocationSchema(
            name=memo.location.name,
            latitude=memo.location.latitude,
            longitude=memo.location.longitude,
            address=memo.location.address,
            category=memo.location.category,
        ),
        user=UserSchema(
            userId=memo.user.user_id,
            username=memo.user.nickname,
            photoUrl=memo.user.profile_image_url
        )
    )

    return APIResponse[MemoSchema](success=True, data=response_data)

