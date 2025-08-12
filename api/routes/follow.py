from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from db.database import get_db
from models.model import FollowEntity, UserEntity
from core.deps import get_current_user
from schemas.follow import FollowActionResponse, FollowListResponse, FollowUserSummary

follow_router = APIRouter(tags=["follow"])  # ✅ prefix 제거

@follow_router.post("/follow/{user_id}", response_model=FollowActionResponse)
def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    if current_user.user_id == user_id:
        return FollowActionResponse(success=False, error="자기 자신은 팔로우할 수 없습니다.")

    target_user = db.query(UserEntity).filter_by(user_id=user_id).first()
    if not target_user:
        return FollowActionResponse(success=False, error="대상 유저가 존재하지 않습니다.")

    existing = db.query(FollowEntity).filter_by(
        follower_id=current_user.user_id,
        following_id=user_id
    ).first()
    if existing:
        return FollowActionResponse(success=False, error="이미 팔로우 요청을 보냈거나 팔로우 중입니다.")

    if target_user.privacy_settings == "closed":
        return FollowActionResponse(success=False, error="해당 유저는 팔로우 요청을 받을 수 없습니다.")
    
    is_approved = target_user.privacy_settings == "open"
    
    current_user.following_count += 1
    target_user.follower_count += 1

    new_follow = FollowEntity(
        follower_id=current_user.user_id,
        following_id=user_id,
        is_approved=is_approved 
    )

    try:
        db.add(new_follow)  
        db.commit()
        return FollowActionResponse(success=True, error=None)
    except Exception as e:
        db.rollback()
        return FollowActionResponse(success=False, error=str(e))


@follow_router.post("/unfollow/{user_id}", response_model=FollowActionResponse)
def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    follow = db.query(FollowEntity).filter_by(
        follower_id=current_user.user_id,
        following_id=user_id
    ).first()

    if not follow:
        return FollowActionResponse(success=False, error="팔로우 관계가 존재하지 않습니다.")

    target_user = db.query(UserEntity).filter_by(user_id=user_id).first()
    try:
        db.delete(follow)
        current_user.following_count -= 1
        target_user.follower_count -= 1
        db.commit()
        #팔로잉 - 1 
        
        return FollowActionResponse(success=True, error=None)
    except Exception as e:
        db.rollback()
        return FollowActionResponse(success=False, error=str(e))

@follow_router.post("/accept/{user_id}", response_model=FollowActionResponse)
def accept_follow_request(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    follow = db.query(FollowEntity).filter_by(
        follower_id=user_id,
        following_id=current_user.user_id
    ).first()

    if not follow:
        return FollowActionResponse(success=False, error="팔로우 요청이 존재하지 않습니다.")

    if follow.is_approved:
        return FollowActionResponse(success=False, error="이미 승인된 팔로우입니다.")
    target_user = db.query(UserEntity).filter_by(user_id=user_id).first()
    try:
        follow.is_approved = True
        current_user.follower_count += 1
        target_user.following_count += 1
        db.commit()
        
        return FollowActionResponse(success=True, error=None)
    except Exception as e:
        db.rollback()
        return FollowActionResponse(success=False, error=str(e))


@follow_router.post("/decline/{user_id}", response_model=FollowActionResponse)
def decline_follow_request(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    follow = db.query(FollowEntity).filter_by(
        follower_id=user_id,
        following_id=current_user.user_id
    ).first()

    if not follow:
        return FollowActionResponse(success=False, error="팔로우 요청이 존재하지 않습니다.")

    if follow.is_approved:
        return FollowActionResponse(success=False, error="이미 승인된 팔로우는 거절할 수 없습니다.")

    try:
        db.delete(follow)
        db.commit()
        return FollowActionResponse(success=True, error=None)
    except Exception as e:
        db.rollback()
        return FollowActionResponse(success=False, error=str(e))

@follow_router.post("/defollow/{user_id}", response_model=FollowActionResponse)
def defollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    follow = db.query(FollowEntity).filter_by(
        follower_id=user_id,
        following_id=current_user.user_id
    ).first()

    if not follow:
        return FollowActionResponse(success=False, error="해당 유저는 현재 나를 팔로우하고 있지 않습니다.")
    target_user = db.query(UserEntity).filter_by(user_id=user_id).first()
    try:
        db.delete(follow)
        current_user.follower_count -= 1
        target_user.following_count -= 1
        db.commit()
        
        return FollowActionResponse(success=True, error=None)
    except Exception as e:
        db.rollback()
        return FollowActionResponse(success=False, error=str(e))
    
@follow_router.get("/follows", response_model=FollowListResponse)
def get_followings(
    limit: int = Query(10, le=50),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    try:
        query = db.query(FollowEntity).filter(FollowEntity.follower_id == current_user.user_id)
        total = query.count()

        follows = query.offset(offset).limit(limit).all()

        result = []
        for follow in follows:
            user = db.query(UserEntity).filter_by(user_id=follow.following_id).first()
            result.append({
                "userId": user.user_id,  # ✅ userId 추가
                "email": user.email,
                "nickname": user.nickname,
                "profileImageUrl": user.profile_image_url,
                "status": "approved" if follow.is_approved else "pending"
            })

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


@follow_router.get("/followers", response_model=FollowListResponse)
def get_followers(
    limit: int = Query(10, le=50),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_user)
):
    try:
        query = db.query(FollowEntity).filter(FollowEntity.following_id == current_user.user_id)
        total = query.count()

        follows = query.offset(offset).limit(limit).all()

        result = []
        for follow in follows:
            user = db.query(UserEntity).filter_by(user_id=follow.follower_id).first()
            result.append({
                "userId": user.user_id,  # ✅ userId 추가
                "email": user.email,
                "nickname": user.nickname,
                "profileImageUrl": user.profile_image_url,
                "status": "approved" if follow.is_approved else "pending"
            })

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
