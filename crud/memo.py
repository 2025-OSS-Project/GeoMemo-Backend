from fastapi import  HTTPException
from sqlalchemy.orm import Session
from models import model
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import model
from datetime import datetime

from schemas.memo import CreateMemoRequest, UpdateMemoRequest

from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from exception.exception import OperatedException, ErrorCode

def create_memo(
    db: Session,
    user_id: int,
    memo_create: CreateMemoRequest
) -> model.MemoEntity:
    # 입력값 검증
    if not memo_create.title or not memo_create.content:
        raise OperatedException(
            status_code=400,
            error_code=ErrorCode.INVALID_INPUT,
            detail="제목과 내용은 필수입니다."
        )
    if not memo_create.location_name or memo_create.location_latitude is None or memo_create.location_longitude is None:
        raise OperatedException(
            status_code=400,
            error_code=ErrorCode.INVALID_INPUT,
            detail="위치 정보(이름, 위도, 경도)는 필수입니다."
        )
    if not memo_create.location_address or not memo_create.location_category:
        raise OperatedException(
            status_code=400,
            error_code=ErrorCode.INVALID_INPUT,
            detail="위치 주소와 카테고리는 필수입니다."
        )
    try:
        # 위치 저장
        location = model.LocationEntity(
            name=memo_create.location_name,
            latitude=round(memo_create.location_latitude, 7),
            longitude=round(memo_create.location_longitude, 7),
            address=memo_create.location_address,
            category=memo_create.location_category
        )
        db.add(location)
        db.commit()
        db.refresh(location)

        # 메모 저장
        memo = model.MemoEntity(
            content=memo_create.content,
            title=memo_create.title,
            is_public=memo_create.is_public,
            user_id=user_id,
            location_id=location.location_id,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        db.add(memo)
        db.commit()
        db.refresh(memo)

        # 사진 저장
        photo = model.PhotoEntity(
            photo_url=memo_create.file_url,
            memo_id=memo.memo_id
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)

        return memo

    except SQLAlchemyError as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.CONNECTION_ERROR,
            detail=f"DB 오류 발생: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류 발생: {str(e)}"
        )

def delete_memo(db: Session, memo_id: int) -> bool:
    memo = db.query(model.MemoEntity).filter(model.MemoEntity.memo_id == memo_id).first()
    if not memo:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.MEMO_NOT_FOUND,
            detail="삭제할 메모가 없습니다."
        )

    location = db.query(model.LocationEntity).filter(model.LocationEntity.location_id == memo.location_id).first()
    if not location:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.LOCATION_NOT_FOUND,
            detail="해당 메모에 연결된 위치를 찾을 수 없습니다."
        )
    try:
        db.delete(location)
        db.delete(memo)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.CONNECTION_ERROR,
            detail=f"DB 오류 발생: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류 발생: {str(e)}"
        )

def update_memo_with_photos(
    db: Session,
    user_id: int,
    memo_id: int,
    memo_update: UpdateMemoRequest
) -> model.MemoEntity:

    # 1️⃣ 의도된 예외 먼저 체크 (404, 403, 400)
    memo = db.query(model.MemoEntity).filter_by(memo_id=memo_id).first()
    if not memo:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.MEMO_NOT_FOUND,
            detail="메모가 존재하지 않습니다."
        )

    if memo.user_id != user_id:
        raise OperatedException(
            status_code=403,
            error_code=ErrorCode.DENIED_PERMISSION,
            detail="해당 메모를 수정할 권한이 없습니다."
        )
    # 2️⃣ DB 작업만 try-except로 감싸기
    try:
        # 메모 수정
        memo.content = memo_update.content
        memo.title = memo_update.title
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

    except SQLAlchemyError as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.CONNECTION_ERROR,
            detail=f"DB 오류 발생: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류 발생: {str(e)}"
        )

def get_memo_detail(db: Session, memo_id: int) -> model.MemoEntity:
    memo = db.query(model.MemoEntity).filter(model.MemoEntity.memo_id == memo_id).first()
    if not memo:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.MEMO_NOT_FOUND,
            detail="메모를 찾을 수 없습니다."
        )
    try:
        return memo
    except SQLAlchemyError as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.CONNECTION_ERROR,
            detail=f"DB 오류 발생: {str(e)}"
        )
    except Exception as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류 발생: {str(e)}"
        )

def get_memo(db: Session, user_id: int):
    memos = db.query(model.MemoEntity).filter(model.MemoEntity.user_id == user_id).all()
    if not memos:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.MEMO_NOT_FOUND,
            detail="해당 사용자의 메모를 찾을 수 없습니다."
        )

    try:
        return memos
    except SQLAlchemyError as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.CONNECTION_ERROR,
            detail=f"DB 오류 발생: {str(e)}"
        )
    except Exception as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류 발생: {str(e)}"
        )

def get_all_memo(
    db: Session,
    user_id: int,
    view_setting: str = "all",
    lat1: float = None,
    lon1: float = None,
    lat2: float = None,
    lon2: float = None
):
    if view_setting not in ("all", "follows", "mine"):
        raise OperatedException(
            status_code=400,
            error_code=ErrorCode.INVALID_INPUT,
            detail=f"유효하지 않은 view_setting 값입니다: {view_setting}"
        )

    query = db.query(model.MemoEntity).join(model.LocationEntity)

    if view_setting == "all":
        query = query.filter(
            model.MemoEntity.is_public == True,
            model.MemoEntity.user_id != user_id
        )
    elif view_setting == "follows":
        following_ids = db.query(model.FollowEntity.following_id)\
            .filter(model.FollowEntity.follower_id == user_id)\
            .subquery()
        query = query.filter(
            model.MemoEntity.user_id.in_(following_ids),
            model.MemoEntity.is_public == True
        )
    elif view_setting == "mine":
        query = query.filter(model.MemoEntity.user_id == user_id)

    if None not in (lat1, lon1, lat2, lon2):
        query = query.filter(
            model.LocationEntity.latitude <= lat1,
            model.LocationEntity.latitude >= lat2,
            model.LocationEntity.longitude >= lon1,
            model.LocationEntity.longitude <= lon2
        )

    try:
        memos = query.all()
        return memos
    except SQLAlchemyError as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.CONNECTION_ERROR,
            detail=f"DB 오류 발생: {str(e)}"
        )
    except Exception as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류: {str(e)}"
        )

def scrap_memo(db: Session, user_id: int, memo_id: int):
    memo = db.query(model.MemoEntity).filter_by(memo_id=memo_id).first()
    if not memo:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.MEMO_NOT_FOUND,
            detail="스크랩하려는 메모가 존재하지 않습니다."
        )

    if not memo.is_public and memo.user_id != user_id:
        raise OperatedException(
            status_code=403,
            error_code=ErrorCode.DENIED_PERMISSION,
            detail="비공개 메모는 스크랩할 수 없습니다."
        )

    exists = db.query(model.MemoScrapEntity).filter_by(
        user_id=user_id, memo_id=memo_id
    ).first()
    if exists:
        raise OperatedException(
            status_code=400,
            error_code=ErrorCode.INVALID_INPUT,
            detail="이미 스크랩한 메모입니다."
        )
    try:
        memo_scrap = model.MemoScrapEntity(user_id=user_id, memo_id=memo_id)
        db.add(memo_scrap)
        db.commit()
        db.refresh(memo_scrap)
        return memo_scrap
    except SQLAlchemyError as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.CONNECTION_ERROR,
            detail=f"DB 오류 발생: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류 발생: {str(e)}"
        )

def unscrap_memo(db: Session, user_id: int, memo_id: int):
    memo_scraped = db.query(model.MemoScrapEntity).filter(
        model.MemoScrapEntity.user_id == user_id,
        model.MemoScrapEntity.memo_id == memo_id
    ).first()
    if not memo_scraped:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.SCRAP_NOT_FOUND,
            detail="해당 스크랩이 존재하지 않습니다."
        )
    try:
        db.delete(memo_scraped)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.CONNECTION_ERROR,
            detail=f"DB 오류 발생: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류 발생: {str(e)}"
        )

def get_scrap_memo(db: Session, user_id: int):
    memos = db.query(model.MemoEntity).join(model.MemoScrapEntity).filter(
        model.MemoScrapEntity.user_id == user_id,
        model.MemoEntity.is_public == True
    ).all()

    if not memos:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.MEMO_NOT_FOUND,
            detail="스크랩한 메모가 없습니다."
        )
    try:
        return memos
    except SQLAlchemyError as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.CONNECTION_ERROR,
            detail=f"DB 오류 발생: {str(e)}"
        )
    except Exception as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류 발생: {str(e)}"
        )