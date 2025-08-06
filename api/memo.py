from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.deps import get_current_user
from models import model
from schemas.memo import CreateMemoRequest, LocationSchema, MemoSchema, UpdateMemoRequest, UserSchema
from schemas.response import APIResponse
from crud.memo import create_memo, delete_memo, get_memo, get_memo_detail, update_memo_with_photos, get_all_memo
from db.database import get_db


router = APIRouter(prefix="/api/memo", tags=["Memo"])

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import List, Optional

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

@router.get("/all")
def read_all_memos(
    view_setting: str = "all",
    db: Session = Depends(get_db),  
    current_user = Depends(get_current_user)
):
    """
    전체 공개 메모 또는 팔로우한 사람의 공개 메모 또는 내 메모 조회
    - view_setting: "all" | "follow" | "mine"
    """
    memos = get_all_memo(db, current_user.user_id, view_setting)
    data = []
    for memo in memos:
        memo_data = {
            "memoId": memo.memo_id,
            "content": memo.content,
            "createdAt": memo.createdAt.isoformat(),
            "updatedAt": memo.updatedAt.isoformat(),
            "isPublic": memo.is_public,
            "fileUrl": [photo.photo_url for photo in memo.photos],  # 리스트 형태 OK
            "location": {
                "name": memo.location.name,
                "latitude": memo.location.latitude,
                "longitude": memo.location.longitude,
                "address": memo.location.address,
                "category": memo.location.category
            },
            "user": {
                "userId": memo.user.user_id,
                "username": memo.user.nickname,
                "photoUrl": memo.user.profile_image_url
            }
        }
        data.append(memo_data)
    return APIResponse[List[MemoSchema]](success=True, data=data, error=None)


@router.get("/{memo_id}")
def memo_info(
    memo_id: int,
    db: Session = Depends(get_db)
):
    memo = get_memo_detail(db,memo_id)
    memo = MemoSchema(
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
    return APIResponse[MemoSchema](success=True, data=memo)


@router.get("/")
def get_all_memos(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memos = get_memo(db, current_user.user_id)
    data = []
    for memo in memos:
        memo_data = {
            "memoId": memo.memo_id,
            "content": memo.content,
            "createdAt": memo.createdAt.isoformat(),
            "updatedAt": memo.updatedAt.isoformat(),
            "isPublic": memo.is_public,
            "fileUrl": [photo.photo_url for photo in memo.photos],  # 리스트 형태 OK
            "location": {
                "name": memo.location.name,
                "latitude": memo.location.latitude,
                "longitude": memo.location.longitude,
                "address": memo.location.address,
                "category": memo.location.category
            },
            "user": {
                "userId": memo.user.user_id,
                "username": memo.user.nickname,
                "photoUrl": memo.user.profile_image_url
            }
        }
        data.append(memo_data)
    return APIResponse[MemoSchema](success=True, data=data)