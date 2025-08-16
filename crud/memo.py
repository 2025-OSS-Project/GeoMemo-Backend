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
        latitude=round(memo_create.location_latitude, 7),
        longitude=round(memo_create.location_longitude,7),
        address=memo_create.location_address,
        category=memo_create.location_category
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    memo = model.MemoEntity(
        content=memo_create.content,
        title = memo_create.title,
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
    memo_id: int,
    memo_update = UpdateMemoRequest
) -> model.MemoEntity:
    memo = db.query(model.MemoEntity).filter_by(memo_id=memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모가 존재하지 않습니다.")

    if memo.user_id != user_id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")

    # 메모 수정
    memo.content = memo_update.content
    memo.title = memo_update.title
    memo.memo_id = memo_id
    memo.is_public = memo_update.is_public
    memo.updatedAt = datetime.utcnow()

    # 기존 사진 중 삭제 대상 제거
    if memo_update.remain_photo_ids is not None:
        db.query(model.PhotoEntity).filter(
            model.PhotoEntity.memo_id == memo_id,
            ~model.PhotoEntity.photo_id.in_(memo_update.remain_photo_ids)
        ).delete(synchronize_session=False)

    # 새 사진 추가
    for url in memo_update.new_photo_urls:
        photo = model.PhotoEntity(photo_url=url, memo_id=memo_id)
        db.add(photo)

    db.commit()
    db.refresh(memo)
    return memo

def get_memo_detail(db: Session, memo_id: int) -> model.MemoEntity:
    memo = db.query(model.MemoEntity).filter(model.MemoEntity.memo_id==memo_id).first()
    if not memo:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다.")
    return memo

def get_memo(db: Session, user_id):
    memos = db.query(model.MemoEntity).filter(model.MemoEntity.user_id == user_id).all()
    if not memos:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다.")
    return memos

def get_all_memo(
    db: Session,
    user_id: int,
    view_setting: str = "all",
    lat1: float = None,  # 왼쪽 위 위도
    lon1: float = None,  # 왼쪽 위 경도
    lat2: float = None,  # 오른쪽 아래 위도
    lon2: float = None   # 오른쪽 아래 경도
):
    # 기본 쿼리: LocationEntity 조인
    query = db.query(model.MemoEntity).join(model.LocationEntity)

    if view_setting == "all":
        query = query.filter(model.MemoEntity.is_public == True,
                             model.MemoEntity.user_id != user_id)

    elif view_setting == "follows":
        # 내가 팔로우한 사람들의 user_id 리스트
        following_ids = db.query(model.FollowEntity.following_id)\
            .filter(model.FollowEntity.follower_id == user_id)\
            .subquery()

        query = query.filter(
            model.MemoEntity.user_id.in_(following_ids),
            model.MemoEntity.is_public == True
        )
    else:
        # 내 메모만
        query = query.filter(model.MemoEntity.user_id == user_id)

    # 좌표 범위 필터 추가
    if None not in (lat1, lon1, lat2, lon2):
        query = query.filter(
            model.LocationEntity.latitude <= lat1,   # 위도: lat1이 더 큼
            model.LocationEntity.latitude >= lat2,
            model.LocationEntity.longitude >= lon1,  # 경도: lon1이 더 작음
            model.LocationEntity.longitude <= lon2
        )

    # 마지막에 한 번만 all()
    memos = query.all()
    return memos


def scrap_memo(db: Session, user_id: int, memo_id: int):
    memo_scrap = model.MemoScrapEntity(
        user_id=user_id,
        memo_id=memo_id
    )
    db.add(memo_scrap)
    db.commit()
    db.refresh(memo_scrap)  # 선택사항: 새로 생성된 ID 등을 확인할 때 유용
    return memo_scrap

def unscrap_memo(db: Session, user_id: int, memo_id: int):
    memo_scraped = db.query(model.MemoScrapEntity).filter(
    model.MemoScrapEntity.user_id == user_id,
    model.MemoScrapEntity.memo_id == memo_id
).first()

    if memo_scraped:
        db.delete(memo_scraped)
        db.commit()
        return True
    
def get_scrap_memo(db: Session, user_id: int):
    memos = db.query(model.MemoEntity).join(model.MemoScrapEntity).filter(
        model.MemoScrapEntity.user_id == user_id,
        model.MemoEntity.is_public == True
    ).all()
    return memos