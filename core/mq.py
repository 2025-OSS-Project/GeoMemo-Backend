# main.py
import asyncio
import json
import os
import threading
import uuid
from typing import Counter, Optional

import boto3
from fastapi import APIRouter, Depends
import redis
from sqlalchemy.orm import Session

from core.deps import get_current_user
from db.database import get_db
from exception.exception import ErrorCode, OperatedException
from models import model

router = APIRouter(prefix="/api/mq", tags=["Mq"])

# ── ENV (SQS & Redis) ─────────────────────────────────────────────────────────
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
EMOTION_REQ_QUEUE_URL = os.getenv("EMOTION_REQ_QUEUE_URL")
INSIGHT_REQ_QUEUE_URL = os.getenv("INSIGHT_REQ_QUEUE_URL")
RECO_REQ_QUEUE_URL    = os.getenv("RECO_REQ_QUEUE_URL")
RECO_RES_QUEUE_URL    = os.getenv("RECO_RES_QUEUE_URL")

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_USER = os.getenv("REDIS_USER")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

if not all([EMOTION_REQ_QUEUE_URL, INSIGHT_REQ_QUEUE_URL, RECO_REQ_QUEUE_URL, RECO_RES_QUEUE_URL]):
    raise RuntimeError("모든 SQS 큐 URL이 필요합니다.")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=6379,
    db=0,
    username=REDIS_USER,
    password=REDIS_PASSWORD,
    ssl=True,
    ssl_cert_reqs=None
)

sqs_client = boto3.client(
    "sqs",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# ── SQS 유틸 ────────────────────────────────────────────────────────────────
def _publish(queue_url: str, message: dict):
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )

# ── 추천 응답 컨슈머 (SQS poll, reco.res만) ─────────────────────────────────
def _consume_reco_responses():
    while True:
        resp = sqs_client.receive_message(
            QueueUrl=RECO_RES_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20
        )
        messages = resp.get("Messages", [])
        for msg in messages:
            try:
                data = json.loads(msg["Body"])
                user_id = data.get("userId")
                if user_id:
                    redis_client.setex(f"reco:{user_id}", 300, json.dumps(data))
            finally:
                # 메시지 삭제
                sqs_client.delete_message(
                    QueueUrl=RECO_RES_QUEUE_URL,
                    ReceiptHandle=msg["ReceiptHandle"]
                )

def consume_messages():
    threading.Thread(target=_consume_reco_responses, daemon=True).start()


# ── 인사이트 생성 / 상태 조회 ──────────────────────────────────────────────────
from datetime import datetime, timedelta

def create_insight_for_user(user_id: int, db: Session):
    now = datetime.now()
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end   = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)

    insight = model.InsightEntity(user_id=user_id, content="인사이트가 생성되는중이에요", status=model.InsightStatus.PENDING)
    db.add(insight)
    db.commit()
    db.refresh(insight)

    memos = db.query(model.MemoEntity).filter(
        model.MemoEntity.user_id == user_id,
        model.MemoEntity.createdAt.between(start, end)
    ).all()

    memo_ids = [m.memo_id for m in memos]
    location_ids = [m.location_id for m in memos if m.location_id]

    emotions = db.query(model.EmotionEntity).filter(model.EmotionEntity.memo_id.in_(memo_ids)).all()
    locations = db.query(model.LocationEntity).filter(model.LocationEntity.location_id.in_(location_ids)).all()

    emotion_map = {e.memo_id: e for e in emotions}
    location_map = {l.location_id: l for l in locations}

    logs = [{
        "timestamp": m.createdAt.isoformat(),
        "label": (emotion_map.get(m.memo_id).emotion_label if emotion_map.get(m.memo_id) else None),
        "score": (emotion_map.get(m.memo_id).emotion_score if emotion_map.get(m.memo_id) else None),
        "category": (location_map.get(m.location_id).category if location_map.get(m.location_id) else None),
        "placeName": (location_map.get(m.location_id).name if location_map.get(m.location_id) else None),
    } for m in memos]

    payload = {"insightId": insight.insight_id, "userId": user_id, "logs": logs}
    _publish(INSIGHT_REQ_QUEUE_URL, payload)
    return {"insightId": insight.insight_id, "status": insight.status}


@router.get("/insights/{user_id}")
def get_insight_status(user_id: int, db: Session = Depends(get_db)):
    user = db.query(model.UserEntity).filter(model.UserEntity.user_id == user_id).first()
    if not user:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.USER_NOT_FOUND,
            detail="해당 사용자가 없습니다."
        )

    now = datetime.now()
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end   = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)

    insight = (
        db.query(model.InsightEntity)
        .filter(model.InsightEntity.user_id == user_id)
        .order_by(model.InsightEntity.createdAt.desc())
        .first()
    )
    if not insight:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.INSIGHT_NOT_FOUND,
            detail="인사이트가 없습니다."
        )

    memos = db.query(model.MemoEntity).filter(
        model.MemoEntity.user_id == user_id,
        model.MemoEntity.createdAt.between(start, end)
    ).all()
    memo_ids = [m.memo_id for m in memos]

    emotions = db.query(model.EmotionEntity).filter(model.EmotionEntity.memo_id.in_(memo_ids)).all()
    emotion_labels = [e.emotion_label for e in emotions if e.emotion_label]
    emotion_count = dict(Counter(emotion_labels))

    return {
        "id": insight.insight_id,
        "status": insight.status,
        "content": insight.content,
        "emotionCount": emotion_count
    }


# ── 장소 추천 API ─────────────────────────────────────────────────────────────
@router.post("/recommend")
def recommend_places(
    user_latitude: float,
    user_longitude: float,
    top: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    lat_min, lat_max = user_latitude - 0.05, user_latitude + 0.05
    lon_min, lon_max = user_longitude - 0.05, user_longitude + 0.05

    memos = (
        db.query(model.MemoEntity)
        .join(model.LocationEntity, model.MemoEntity.location_id == model.LocationEntity.location_id)
        .filter(
            model.LocationEntity.latitude.between(lat_min, lat_max),
            model.LocationEntity.longitude.between(lon_min, lon_max),
            model.MemoEntity.is_public == True
        )
        .all()
    )

    location_ids = list({m.location_id for m in memos if m.location_id is not None})
    locations = db.query(model.LocationEntity).filter(model.LocationEntity.location_id.in_(location_ids)).all()

    candidates = [
        {
            "placeId": loc.location_id,
            "name": loc.name,
            "category": loc.category,
            "latitude": float(loc.latitude or 0),
            "longitude": float(loc.longitude or 0),
        }
        for loc in locations
    ]

    # ── context ──
    recent_memo = (
        db.query(model.MemoEntity)
        .filter(model.MemoEntity.user_id == current_user.user_id)
        .order_by(model.MemoEntity.createdAt.desc())
        .first()
    )
    recent_emotion = None
    if recent_memo:
        emotions = (
            db.query(model.EmotionEntity)
            .filter(model.EmotionEntity.memo_id == recent_memo.memo_id)
            .all()
        )
        recent_emotion = [{"label": e.emotion_label, "score": e.emotion_score} for e in emotions]

    user_memos = (
        db.query(model.MemoEntity)
        .join(model.LocationEntity, model.MemoEntity.location_id == model.LocationEntity.location_id)
        .filter(model.MemoEntity.user_id == current_user.user_id)
        .all()
    )
    fav_categories = dict(Counter([m.location.category for m in user_memos if m.location and m.location.category]))

    scrap_place_ids = [
        s.memo.location_id
        for s in db.query(model.MemoScrapEntity)
        .join(model.MemoEntity, model.MemoScrapEntity.memo_id == model.MemoEntity.memo_id)
        .filter(model.MemoScrapEntity.user_id == current_user.user_id)
        .all()
        if s.memo and s.memo.location_id
    ]

    followed_user_ids = [
        f.following_id
        for f in db.query(model.FollowEntity)
        .filter(model.FollowEntity.follower_id == current_user.user_id, model.FollowEntity.is_approved == True)
        .all()
    ]

    place_signals = []
    for loc in locations:
        memos_for_loc = db.query(model.MemoEntity).filter(model.MemoEntity.location_id == loc.location_id).all()
        if not memos_for_loc:
            pos_ratio = 0.0
            followed_pos_count = 0
        else:
            total = 0
            pos = 0
            followed_pos_count = 0
            for m in memos_for_loc:
                emotions = db.query(model.EmotionEntity).filter(model.EmotionEntity.memo_id == m.memo_id).all()
                for e in emotions:
                    total += 1
                    if e.emotion_label == "긍정":
                        pos += 1
                        if m.user_id in followed_user_ids:
                            followed_pos_count += 1
            pos_ratio = pos / total if total > 0 else 0.0

        place_signals.append({
            "placeId": loc.location_id,
            "posRatio": round(pos_ratio, 2),
            "followedPositiveCount": followed_pos_count,
        })

    context = {
        "recentEmotion": recent_emotion,
        "favCategories": fav_categories,
        "scrapPlaceIds": scrap_place_ids,
        "followedUserIds": followed_user_ids,
        "placeSignals": place_signals,
    }

    corr_id = str(uuid.uuid4())
    payload = {
        "userId": current_user.user_id,
        "top": top,
        "candidates": candidates,
        "context": context,
        "debug": True
    }
    _publish(RECO_REQ_QUEUE_URL, payload)

    return {
        "requestId": corr_id,
        "queued": True,
        "candidateCount": len(candidates)
    }


# ── 감정 분석 API ───────────────────────────────────────────────────────────
@router.post("/emotion_analysis/{memo_id}")
def emotion_analysis(memo_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    memo = db.query(model.MemoEntity).filter_by(memo_id=memo_id).first()
    if not memo:
        raise OperatedException(
            status_code=404,
            error_code=ErrorCode.MEMO_NOT_FOUND,
            detail="해당 메모를 찾을 수 없습니다."
        )
    try:
        payload = {"userId": current_user.user_id, "memoId": memo.memo_id, "content": memo.content}
        _publish(EMOTION_REQ_QUEUE_URL, payload)
        return {"memo_id": memo.memo_id, "queued": True}
    except Exception as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류 발생: {str(e)}"
        )


# ── 추천 결과 조회 API ───────────────────────────────────────────────────────
@router.get("/recommendations/{user_id}")
def get_recommendations(user_id: int):
    try:
        result = redis_client.get(f"reco:{user_id}")
        if not result:
            raise OperatedException(
                status_code=404,
                error_code=ErrorCode.MEMO_NOT_FOUND,
                detail="추천 결과가 아직 없습니다."
            )
        return json.loads(result)
    except redis.exceptions.RedisError as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.CONNECTION_ERROR,
            detail=f"Redis 오류 발생: {str(e)}"
        )
    except Exception as e:
        raise OperatedException(
            status_code=500,
            error_code=ErrorCode.UNEXPECTED_ERROR,
            detail=f"예상치 못한 오류 발생: {str(e)}"
        )
