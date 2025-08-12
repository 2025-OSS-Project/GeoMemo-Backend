# main.py
import json
import os
import pika
from fastapi import APIRouter, FastAPI, Depends
from sqlalchemy.orm import Session
from core.deps import get_current_user
from crud.memo import get_all_memo
from db.database import get_db
from models import model


router = APIRouter(prefix="/api/mq", tags=["Mq"])

RABBITMQ_URL = os.getenv("RAABITMQ_URL")  # AWS MQ 브로커 URL
QUEUE_NAME = "geomemo"

params = pika.URLParameters(RABBITMQ_URL)
connection = pika.BlockingConnection(params)
channel = connection.channel()
channel.queue_declare(queue=QUEUE_NAME, durable=True)

def publish_to_mq(message: dict):
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2  # persistent
        )
    )


@router.post("/insights")
def create_insight(
    lat1: float = None,  # 왼쪽 위 위도
    lon1: float = None,  # 왼쪽 위 경도
    lat2: float = None,  # 오른쪽 아래 위도
    lon2: float = None,   # 오른쪽 아래 경도
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    ):
    # 1. 상태 PENDING으로 DB insert
    insight = model.InsightEntity(
        user_id=current_user.user_id,
        status=model.InsightStatus.PENDING
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    memos = get_all_memo(db, current_user.user_id, "all", lat1, lon1, lat2, lon2)

    memo_ids = [m.memo_id for m in memos]
    location_ids = [memo.location_id for memo in memos if memo.location_id is not None]

    # 감정, 위치 쿼리   
    emotions = db.query(model.EmotionEntity).filter(model.EmotionEntity.memo_id.in_(memo_ids)).all()
    locations = db.query(model.LocationEntity).filter(
    model.LocationEntity.location_id.in_(location_ids)
    ).all()

    # 메모ID 기준으로 dict로 매핑
    emotion_map = {e.memo_id: e for e in emotions}
    location_map = {l.location_id: l for l in locations}

    result = []
    for memo in memos:
        emotion = emotion_map.get(memo.memo_id)
        location = location_map.get(memo.location_id)  # location_id 기준 조회
        result.append({
        "timestamp": memo.createdAt.isoformat(),
        "label": emotion.emotion_label if emotion else None,
        "score": emotion.emotion_score if emotion else None,
        "category": location.category if location else None,
        "placeName": location.name if location else None,
        })
    mq_message = {
        "userId": current_user.user_id,
        "logs": result
    }
    publish_to_mq(mq_message)

    return {"insightId": insight.insight_id, "status": insight.status}

@router.get("/insights/{user_id}")
def get_insight_status(user_id: int, db: Session = Depends(get_db)):
    insight = db.query(model.InsightEntity).filter(model.InsightEntity.user_id == user_id).first()
    if not insight:
        return {"error": "Not found"}
    return {
        "id": insight.insight_id,
        "status": insight.status,
        "content": insight.content
    }
