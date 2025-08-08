from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from core.deps import get_current_user
from models import model
from schemas.memo import CreateMemoRequest, LocationSchema, MemoSchema, MemoScrapSchema, UpdateMemoRequest, UserSchema
from schemas.response import APIResponse
from crud.memo import (
    create_memo, delete_memo, get_memo, get_memo_detail,
    get_scrap_memo, scrap_memo, unscrap_memo,
    update_memo_with_photos, get_all_memo
)
from db.database import get_db

router = APIRouter(prefix="/api/memo", tags=["Memo"])

@router.post("/", response_model=APIResponse[MemoSchema])
async def create_memo_api(
    memo_create: CreateMemoRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    memo = create_memo(
        db=db,
        user_id=current_user.user_id,
        memo_create=memo_create,
    )

    memo_schema = MemoSchema(
        memoId=memo.memo_id,
        title =memo.title,
        content=memo.content,
        createdAt=memo.createdAt,
        updatedAt=memo.updatedAt,
        isPublic=memo.is_public,
        fileUrl=[photo.photo_url for photo in memo.photos],
        location=LocationSchema(
            name=memo_create.location_name,
            latitude=memo_create.location_latitude,
            longitude=memo_create.location_longitude,
            address=memo_create.location_address,
            category=memo_create.location_category,
        ),
        user=UserSchema(
            userId=memo.user.user_id,
            username=memo.user.nickname,
            photoUrl=memo.user.profile_image_url,
        ),
    )

    return APIResponse(success=True, data=memo_schema)


@router.post("/delete/{memo_id}", response_model=APIResponse[int])
def delete_memo_api(memo_id: int, db: Session = Depends(get_db)):
    delete_memo(db, memo_id)
    return APIResponse(success=True, data=memo_id)


@router.post("/update/{memo_id}", response_model = APIResponse[MemoSchema])
async def update_memo_api(
    memo_update: UpdateMemoRequest,
    memo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    memo = update_memo_with_photos(
        db=db,
        user_id=current_user.user_id,
        memo_id = memo_id,
        memo_update=memo_update,
    )

    response_data = MemoSchema(
        memoId=memo.memo_id,
        title=memo.title,
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
            photoUrl=memo.user.profile_image_url,
        ),
    )

    return APIResponse(success=True, data=response_data)


@router.get("/all")
def read_all_memos(
    view_setting: str = "all",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    memos = get_all_memo(db, current_user.user_id, view_setting)
    data = []
    for memo in memos:
        memo_data = {
            "memoId": memo.memo_id,
            "content": memo.content,
            "createdAt": memo.createdAt.isoformat(),
            "updatedAt": memo.updatedAt.isoformat(),
            "isPublic": memo.is_public,
            "fileUrl": [photo.photo_url for photo in memo.photos],
            "location": {
                "name": memo.location.name,
                "latitude": memo.location.latitude,
                "longitude": memo.location.longitude,
                "address": memo.location.address,
                "category": memo.location.category,
            },
            "user": {
                "userId": memo.user.user_id,
                "username": memo.user.nickname,
                "photoUrl": memo.user.profile_image_url,
            },
        }
        data.append(memo_data)
    return APIResponse(success=True, data=data)


@router.get("/scrap", response_model=APIResponse[List[MemoSchema]])
def get_scrapped_memos(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    memos = get_scrap_memo(db, current_user.user_id)
    data = []
    for memo in memos:
        memo_data = {
            "memoId": memo.memo_id,
            "title": memo.title,
            "content": memo.content,
            "createdAt": memo.createdAt.isoformat(),
            "updatedAt": memo.updatedAt.isoformat(),
            "isPublic": memo.is_public,
            "fileUrl": [photo.photo_url for photo in memo.photos],
            "location": {
                "name": memo.location.name,
                "latitude": memo.location.latitude,
                "longitude": memo.location.longitude,
                "address": memo.location.address,
                "category": memo.location.category,
            },
            "user": {
                "userId": memo.user.user_id,
                "username": memo.user.nickname,
                "photoUrl": memo.user.profile_image_url,
            },
        }
        data.append(memo_data)

    return APIResponse(success=True, data=data)


@router.get("/{memo_id}", response_model=APIResponse[MemoSchema])
def memo_info(
    memo_id: int,
    db: Session = Depends(get_db),
):
    memo = get_memo_detail(db, memo_id)
    memo_schema = MemoSchema(
        memoId=memo.memo_id,
        title=memo.title,
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
            photoUrl=memo.user.profile_image_url,
        ),
    )
    return APIResponse(success=True, data=memo_schema)


@router.get("/", response_model=APIResponse[List[MemoSchema]])
def get_all_memos(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memos = get_memo(db, current_user.user_id)
    data = []
    for memo in memos:
        memo_data = {
            "memoId": memo.memo_id,
            "title": memo.title,
            "content": memo.content,
            "createdAt": memo.createdAt.isoformat(),
            "updatedAt": memo.updatedAt.isoformat(),
            "isPublic": memo.is_public,
            "fileUrl": [photo.photo_url for photo in memo.photos],
            "location": {
                "name": memo.location.name,
                "latitude": memo.location.latitude,
                "longitude": memo.location.longitude,
                "address": memo.location.address,
                "category": memo.location.category,
            },
            "user": {
                "userId": memo.user.user_id,
                "username": memo.user.nickname,
                "photoUrl": memo.user.profile_image_url,
            },
        }
        data.append(memo_data)
    return APIResponse(success=True, data=data)


@router.post("/scrap/{memo_id}", response_model=APIResponse[MemoScrapSchema])
def scrap_memo_route(
    memo_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scrap = scrap_memo(db, current_user.user_id, memo_id)
    data = {
        "scrap_id": scrap.scrap_id,
        "createdAt": scrap.createdAt.isoformat(),
        "user_id": scrap.user_id,
        "memo_id": scrap.memo_id,
    }
    return APIResponse(success=True, data=data)


@router.post("/unscrap/{memo_id}")
def unscrap_memo_route(
    memo_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    unscrap_memo(db, current_user.user_id, memo_id)
    return APIResponse(success=True, data=None)
