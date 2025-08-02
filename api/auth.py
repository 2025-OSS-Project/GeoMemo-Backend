from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.database import get_db
from crud import user as crud_user
from schemas.user import UserCreate, UserLogin
from schemas.token import Token
from core.jwt import create_access_token
from core.security import verify_password
from models.model import UserEntity, EmailVerifyEntity
from datetime import datetime
from core.deps import get_current_user
import random

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    # 이메일 중복 체크
    existing_user = crud_user.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다."
        )

    # 사용자 생성
    new_user = crud_user.create_user(db, user)

    # 응답 반환
    return {
        "message": "회원가입 완료",
        "user_id": new_user.user_id,
        "email": new_user.email
    }

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user_db: UserEntity = crud_user.get_user_by_email(db, user_data.email)
    if not user_db or not verify_password(user_data.password, user_db.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(data={"sub": str(user_db.user_id)})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
def get_my_profile(current_user: UserEntity = Depends(get_current_user)):
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "name": current_user.name,
        "nickname": current_user.nickname,
        "phone": current_user.phone,
        "profile_image_url": current_user.profile_image_url,
        "privacy_settings": current_user.privacy_settings,
        "view_settings": current_user.view_settings
    }

@router.post("/send-mail")
def send_mail(email: str, db: Session = Depends(get_db)):
    user = crud_user.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="해당 이메일로 등록된 유저가 없습니다.")

    # 6자리 숫자 코드 생성
    code = random.randint(100000, 999999)

    # 기존 인증 레코드 삭제 또는 무효화
    db.query(EmailVerifyEntity).filter(EmailVerifyEntity.user_id == user.user_id).delete()

    # 새 인증코드 저장
    verify_entry = EmailVerifyEntity(
        user_id=user.user_id,
        verification_code=code,
        is_verified=False,
        requested_at=datetime.utcnow(),
        verified_at=None
    )
    db.add(verify_entry)
    db.commit()

    # 실제 이메일 전송은 생략 (모의 출력)
    print(f"[MOCK] {email} → 인증코드: {code}")

    return {"message": "인증코드가 이메일로 전송되었습니다 (모의)", "email": email}

@router.post("/check-mail")
def check_mail(email: str, code: str, db: Session = Depends(get_db)):
    user = crud_user.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="해당 이메일로 등록된 유저가 없습니다.")

    entry = db.query(EmailVerifyEntity).filter(
        EmailVerifyEntity.user_id == user.user_id,
        EmailVerifyEntity.verification_code == int(code),
        EmailVerifyEntity.is_verified == False
    ).first()

    if not entry:
        raise HTTPException(status_code=400, detail="인증코드가 일치하지 않거나 이미 인증되었습니다.")

    entry.is_verified = True
    entry.verified_at = datetime.utcnow()
    db.commit()

    return {"message": "이메일 인증이 완료되었습니다", "email": email}