from fastapi import APIRouter, Depends, Query, HTTPException
from core.deps import get_current_user
from models.model import UserEntity, FollowEntity
from schemas.user import DeleteUserResponse, NicknameUpdateRequest, NicknameUpdateResponse, PasswordUpdateRequest, PasswordUpdateResponse, UserProfileImageUpdate, PrivacyUpdateRequest, StandardResponse
from crud.user import delete_user, update_user_nickname, update_user_password
from db.database import get_db
from sqlalchemy.orm import Session, aliased
from sqlalchemy import case, literal
from enum import Enum
from api.routes.follow import follow_router  # ✅ follow 라우터 import

router = APIRouter(
    prefix="/api/user",
    tags=["user"]
)

router.include_router(follow_router)

class SearchType(str, Enum):
    nickname = "nickname"
    email = "email"

@router.post("/update-password", response_model=PasswordUpdateResponse)
def update_password(
    body: PasswordUpdateRequest,
    current_user: UserEntity = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    return update_user_password(session, current_user.user_id, body.password, body.new_password)


@router.post("/update-nickname", response_model=NicknameUpdateResponse)
def update_nickname(
    body: NicknameUpdateRequest,
    current_user: UserEntity = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    return update_user_nickname(session, current_user.user_id, body.nickname)

@router.post("/delete-account", response_model=DeleteUserResponse)
def delete_account(
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return delete_user(current_user.user_id, db)

@router.post("/profile-image")
def update_profile_image(
    payload: UserProfileImageUpdate,
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    try:
        current_user.profile_image_url = payload.profile_image_url
        db.commit()
        db.refresh(current_user)
        return {
            "success": True,
            "error": None
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/search")
def search_users(
    keyword: str = Query(..., min_length=1),
    type: SearchType = Query(..., description="검색 타입: nickname 또는 email"),
    limit: int = Query(10, le=50, description="한 페이지당 결과 수"),
    offset: int = Query(0, description="건너뛸 유저 수"),
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)  # ✅ JWT 인증 필요(나 기준)
):
    try:
        # 1) 기본 검색 집합: 본인 제외 + closed 제외
        base_q = db.query(UserEntity).filter(
            UserEntity.user_id != current_user.user_id,
            UserEntity.privacy_settings != 'closed',
        )

        # 2) 키워드 필터(부분일치). 대소문자 무시 원하면 ilike로 교체 가능
        if type == SearchType.nickname:
            base_q = base_q.filter(UserEntity.nickname.like(f"%{keyword}%"))
        elif type == SearchType.email:
            base_q = base_q.filter(UserEntity.email.like(f"%{keyword}%"))
        else:
            raise HTTPException(status_code=400, detail="invalid search type")

        # 페이지네이션 total
        total = base_q.count()

        # 3) 나→상대 팔로우 상태 조인 (LEFT JOIN)
        F = aliased(FollowEntity)
        q = (
            db.query(
                UserEntity.user_id.label("user_id"),
                UserEntity.email.label("email"),
                UserEntity.nickname.label("nickname"),
                UserEntity.profile_image_url.label("profile_image_url"),
                case(
                    (
                        (F.following_id.is_(None)),
                        literal(0)  # 관계 없음 → status=0 (팔로우하기)
                    ),
                    (
                        (F.is_approved.is_(False)),
                        literal(1)  # 요청 보냄/미승인 → status=1 (승인 대기중)
                    ),
                    else_=literal(2)  # 승인됨 → status=2 (팔로우 중)
                ).label("status"),
            )
            .outerjoin(
                F,
                (F.follower_id == current_user.user_id) &
                (F.following_id == UserEntity.user_id)
            )
            .filter(UserEntity.user_id != current_user.user_id)
            .filter(UserEntity.privacy_settings != 'closed')
        )

        # 키워드 동일 적용
        if type == SearchType.nickname:
            q = q.filter(UserEntity.nickname.like(f"%{keyword}%"))
        else:
            q = q.filter(UserEntity.email.like(f"%{keyword}%"))

        rows = (
            q.order_by(UserEntity.nickname.asc(), UserEntity.user_id.asc())
             .offset(offset)
             .limit(limit)
             .all()
        )

        result = [
            {
                "userId": r.user_id,
                "username": r.email,
                "nickname": r.nickname,
                "profileImageUrl": r.profile_image_url,
                "status": int(r.status),  # 0/1/2
            }
            for r in rows
        ]

        return {
            "success": True,
            "data": {
                "users": result,
                "total": total
            },
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }

    
@router.post("/update-privacy", response_model=StandardResponse)
def update_privacy(
    payload: PrivacyUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    try:
        current_user.privacy_settings = payload.privacy_settings
        db.commit()
        return {"success": True, "error": None}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    
from schemas.user import ViewUpdateRequest

@router.post("/update-view", response_model=StandardResponse)
def update_view_settings(
    payload: ViewUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    try:
        current_user.view_settings = payload.view_settings
        db.commit()
        return {"success": True, "error": None}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
