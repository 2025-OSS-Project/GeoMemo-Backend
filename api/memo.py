from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from core.deps import get_current_user
from schemas.memo import MemoResponse
from schemas.response import APIResponse
from crud.memo import create_memo_with_file, delete_memo, update_memo_with_file
from db.database import get_db
from fastapi import Form, File, UploadFile


router = APIRouter(prefix="/api/memo", tags=["Memo"])

@router.post("/")
async def create_memo(
    content: str = Form(...),
    isPublic: bool = Form(...),
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    location_data = {
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "address": address,
        "category": category,
    }

    memo = create_memo_with_file(
        db=db,
        content=content,
        is_public=isPublic,
        user_id=current_user.user_id,
        location_info=location_data,
        file=file
    )

    # 수동 직렬화
    data = {
        "memoId": memo.memo_id,
        "content": memo.content,
        "createdAt": memo.createdAt.isoformat(),
        "updatedAt": memo.updatedAt.isoformat(),
        "isPublic": memo.is_public,
        "fileUrls": [photo.photo_url for photo in memo.photos],
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

    return APIResponse(success=True, data=data, error=None)


@router.post("/delete/{memo_id}")
def delete_memo_api(memo_id: int, db: Session = Depends(get_db)):
    result = delete_memo(db, memo_id)
    return APIResponse(success=True, data=memo_id, error=None)

@router.post("/{memo_id}")
async def update_memo_api(
    memo_id: int,
    content: str = Form(...),
    isPublic: bool = Form(...),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
   
    # 메모 수정 함수 호출
    memo = update_memo_with_file(
        db=db,
        memo_id=memo_id,
        content=content,
        is_public=isPublic,
        user_id=current_user.user_id,
        file=file
    )
    data = {
        "memoId": memo.memo_id,
        "content": memo.content,
        "createdAt": memo.createdAt.isoformat(),
        "updatedAt": memo.updatedAt.isoformat(),
        "isPublic": memo.is_public,
        "fileUrl": memo.file_url,
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

    return APIResponse(success=True, data=data, error=None)
