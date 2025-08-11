from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.database import get_db
from crud import user as crud_user
from schemas.user import UserCreate, UserLogin
from schemas.token import Token
from core.jwt import create_access_token
from core.security import verify_password
from models.model import UserEntity, EmailVerifyEntity
from datetime import datetime, timedelta
from core.deps import get_current_user
import random
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
load_dotenv()  # .env 파일 로드

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

# --- Gmail SMTP 발송 헬퍼 ---
def send_email_gmail(to_email: str, subject: str, body: str):
    smtp_user = os.getenv("SMTP_USER")   # 예: yourname@gmail.com
    smtp_pass = os.getenv("SMTP_PASS")   # 예: 앱 비밀번호 (일반 비번 X)
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not smtp_user or not smtp_pass:
        # 설정 누락 시 개발 단계에서는 예외 대신 로그만 남기고 패스해도 됨
        print("[WARN] SMTP_USER/SMTP_PASS not set. Skipping real email send.")
        print(f"[MOCK] {to_email} → {subject}\n{body}")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as s:
        s.ehlo()
        s.starttls()
        s.login(smtp_user, smtp_pass)
        s.send_message(msg)

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

# --- /login 교체: 이메일 인증 필수 + 24시간 만료 시 탈퇴 처리 ---
@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user_db: UserEntity = crud_user.get_user_by_email(db, user_data.email)
    if not user_db or not verify_password(user_data.password, user_db.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # 최신 인증 상태 조회 (단일 레코드 정책 기준)
    entry: EmailVerifyEntity | None = db.query(EmailVerifyEntity)\
        .filter(EmailVerifyEntity.user_id == user_db.user_id)\
        .order_by(EmailVerifyEntity.requested_at.desc())\
        .first()

    # (1) 인증 엔트리가 없거나, 인증이 완료되지 않았다면 로그인 거부
    if not entry or entry.is_verified is False:
        # (2) 미인증 상태이고, 최초(또는 최근) 요청 시점으로부터 24시간 경과 시 회원 삭제
        if entry and entry.requested_at and (datetime.utcnow() - entry.requested_at) >= timedelta(hours=24):
            try:
                # 관련 인증 레코드 삭제
                db.query(EmailVerifyEntity).filter(EmailVerifyEntity.user_id == user_db.user_id).delete(synchronize_session=False)
                # 유저 삭제
                db.delete(user_db)
                db.commit()
            except Exception:
                db.rollback()
                raise HTTPException(status_code=500, detail="만료 처리 중 오류가 발생했습니다.")
            # 24시간 경과 알림
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이메일 인증 요청 후 24시간이 지나 가입이 만료되었습니다. 다시 회원가입을 진행해주세요."
            )

        # 24시간 이내라면 단순히 인증 필요 안내
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 인증이 완료되지 않았습니다. 메일함에서 인증을 완료해주세요."
        )

    # (인증 완료) → 토큰 발급
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

# --- /send-mail 교체 ---
@router.post("/send-mail")
def send_mail(email: str, db: Session = Depends(get_db)):
    user = crud_user.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="해당 이메일로 등록된 유저가 없습니다.")

    # 6자리 숫자 코드 생성
    code = random.randint(100000, 999999)

    # 기존 인증 레코드 제거 (가장 단순한 정책)
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

    # 실제 이메일 전송 (지메일 SMTP)
    subject = "[GeoMemo] 이메일 인증 코드"
    body = f"""다음 인증코드를 입력해주세요.

인증코드: {code}

본 메일은 인증 요청에 따라 자동 발송되었습니다. (유효기간: 24시간)
"""
    try:
        send_email_gmail(email, subject, body)
    except Exception as e:
        # 발송 실패 시 롤백할지 여부는 정책에 따라. 여기선 코드 저장은 유지하고 경고만.
        print(f"[ERROR] Email send failed: {e}")

    return {"message": "인증코드가 이메일로 전송되었습니다", "email": email}


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