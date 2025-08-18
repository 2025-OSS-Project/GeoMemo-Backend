from datetime import datetime
from db.database import get_db
from models.model import UserEntity
from sqlalchemy.orm import Session
from core.mq import create_insight_for_user
def daily_job():
    db: Session = next(get_db())  # DB 세션 가져오기
    users = db.query(UserEntity).all()  # 모든 사용자 조회

    for user in users:
        user_id = user.user_id
        print(f"[{datetime.now().isoformat()}] User {user_id}: 작업 시작")

        # 기존 API 내부 로직 그대로 함수로 호출

        create_insight_for_user(user_id, db)

        print(f"[{datetime.now().isoformat()}] User {user_id}: 작업 완료")