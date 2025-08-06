from fastapi import  HTTPException
from sqlalchemy.orm import Session
from models import model
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import model
from datetime import datetime

from schemas.memo import CreateMemoRequest, UpdateMemoRequest

def create_memo(
    db: Session,
    user_id: int,
    memo_create: CreateMemoRequest
) -> model.MemoEntity:
    location = model.LocationEntity(
        name=memo_create.location_name,
        latitude=memo_create.location_latitude,
        longitude=memo_create.location_longitude,
        address=memo_create.location_address,
        category=memo_create.location_category
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    memo = model.MemoEntity(
        content=memo_create.content,
        is_public=memo_create.is_public,
        user_id=user_id,
        location_id = location.location_id,
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)

    photo = model.PhotoEntity(
        photo_url=memo_create.file_url,
        memo_id=memo.memo_id
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return memo


def delete_memo(db: Session, memo_id: int) -> bool:
    memo = db.query(model.MemoEntity).filter(model.MemoEntity.memo_id==memo_id).first()
    location = db.query(model.LocationEntity).filter(model.LocationEntity.location_id==memo.location_id).first()
    db.delete(location)
    if not memo:
        raise HTTPException(status_code=404, detail="삭제할 메모가 없습니다.")
    db.delete(memo)
    db.commit()
    return True

def update_memo_with_photos(
    db: Session,
    user_id: int,
    memo_update = UpdateMemoRequest
) -> model.MemoEntity:
    memo = db.query(model.MemoEntity).filter_by(memo_id=memo_update.memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모가 존재하지 않습니다.")

    if memo.user_id != user_id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")

    # 메모 수정
    memo.content = memo_update.content
    memo.is_public = memo_update.is_public
    memo.updatedAt = datetime.utcnow()

    # 기존 사진 중 삭제 대상 제거
    if memo_update.remain_photo_ids is not None:
        db.query(model.PhotoEntity).filter(
            model.PhotoEntity.memo_id == memo_update.memo_id,
            ~model.PhotoEntity.photo_id.in_(memo_update.remain_photo_ids)
        ).delete(synchronize_session=False)

    # 새 사진 추가
    for url in memo_update.new_photo_urls:
        photo = model.PhotoEntity(photo_url=url, memo_id=memo_update.memo_id)
        db.add(photo)

    db.commit()
    db.refresh(memo)
    return memo


