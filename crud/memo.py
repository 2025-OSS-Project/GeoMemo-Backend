
from typing import Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from models import model
from datetime import datetime

from schemas.memo import LocationInfo

#메모추가
from typing import Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from models import model
from datetime import datetime

from schemas.memo import LocationInfo

def create_memo_with_file(
    db: Session,
    content: str,
    is_public: bool,
    user_id: int,
    location_info: LocationInfo,
    file: UploadFile = None
) -> model.MemoEntity:
    location_data = LocationInfo(**location_info)
    location = model.LocationEntity(
    name=location_data.name,
    latitude=location_data.latitude,
    longitude=location_data.longitude,
    address=location_data.address,
    category=location_data.category
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    memo = model.MemoEntity(
        content=content,
        is_public=is_public,
        user_id=user_id,
        location_id = location.location_id,
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)

    photo = model.PhotoEntity
    # 파일 업로드 처리
    if file:
        saved_path = f"uploads/{file.filename}"
        photo = model.PhotoEntity(
            photo_url=saved_path,
            memo_id=memo.memo_id
        )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    # 필요시 memo.photos.append(photo) 가능

    return memo


def delete_memo(db: Session, memo_id: int) -> bool:
    memo = db.query(model.MemoEntity).filter_by(memo_id=memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="삭제할 메모가 없습니다.")
    db.delete(memo)
    db.commit()
    return True

def update_memo_with_file(
    db: Session,
    memo_id: int,
    content: str,
    is_public: bool,
    user_id: int,
    file: UploadFile = None
) -> model.MemoEntity:
    memo = db.query(model.MemoEntity).filter_by(memo_id=memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모가 존재하지 않습니다.")

    if memo.user_id != user_id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")

    # 메모 정보 업데이트
    memo.content = content
    memo.is_public = is_public
    memo.updatedAt = datetime.utcnow()

    # 파일 업로드 처리
    if file:
        # 실제 업로드는 별도 함수로 대체 가능
        saved_path = f"uploads/{file.filename}"
        memo.file_url = saved_path

    db.commit()
    db.refresh(memo)
    return memo
