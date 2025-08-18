# main.py
import asyncio
import json
import os
import threading
import uuid
from typing import Counter, Dict, Optional

import pika
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
import redis
from sqlalchemy.orm import Session

from core.deps import get_current_user
from core.jwt import decode_access_token
from db.database import get_db
from models import model

router = APIRouter(prefix="/api/mq", tags=["Mq"])

# ── ENV (RabbitMQ & Queues) ──────────────────────────────────────────────────
AMQP_URL = os.getenv("AMQP_URL")  # amqps://...:5671/(vhost)
if not AMQP_URL:
    raise RuntimeError("AMQP_URL is required")

EMOTION_REQ_QUEUE = os.getenv("EMOTION_REQ_QUEUE", "emotion.req")
INSIGHT_REQ_QUEUE = os.getenv("INSIGHT_REQ_QUEUE", "insight.req")
RECO_REQ_QUEUE    = os.getenv("RECO_REQ_QUEUE",    "reco.req")
RECO_RES_QUEUE    = os.getenv("RECO_RES_QUEUE",    "reco.res")

MQ_QUEUE_TYPE   = os.getenv("MQ_QUEUE_TYPE")       # e.g. "quorum"
EMOTION_TTL_MS  = os.getenv("EMOTION_TTL_MS")      # e.g. "600000"
INSIGHT_TTL_MS  = os.getenv("INSIGHT_TTL_MS")      # e.g. "900000"
RECO_TTL_MS     = os.getenv("RECO_TTL_MS")         # e.g. "300000"

redis_client = redis.Redis(
    host="host.docker.internal",  # 호스트 EC2의 Redis 접근
    port=6379,                    # Redis 기본 포트
    db=0                           # 사용할 DB 번호
)

def _queue_args(ttl_ms: Optional[str]) -> dict:
    args = {}
    if MQ_QUEUE_TYPE:
        args["x-queue-type"] = MQ_QUEUE_TYPE
    if ttl_ms and ttl_ms.isdigit():
        args["x-message-ttl"] = int(ttl_ms)
    return args

# ── RabbitMQ 유틸 ────────────────────────────────────────────────────────────
def _declare_queue(ch, name: str, ttl_env: Optional[str] = None):
    ch.queue_declare(queue=name, durable=True, arguments=_queue_args(ttl_env))

def _publish(queue_name: str, message: dict, *, reply_to: str = None, correlation_id: str = None):
    """기본 익스체인지("")로 큐 이름에 라우팅"""
    params = pika.URLParameters(AMQP_URL)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()

    # 대상 큐/응답 큐 존재 보장
    if queue_name == EMOTION_REQ_QUEUE:
        _declare_queue(ch, EMOTION_REQ_QUEUE, EMOTION_TTL_MS)
    elif queue_name == INSIGHT_REQ_QUEUE:
        _declare_queue(ch, INSIGHT_REQ_QUEUE, INSIGHT_TTL_MS)
    elif queue_name == RECO_REQ_QUEUE:
        _declare_queue(ch, RECO_REQ_QUEUE, RECO_TTL_MS)
    else:
        _declare_queue(ch, queue_name, None)

    if reply_to:
        _declare_queue(ch, reply_to, None)

    props = pika.BasicProperties(
        delivery_mode=2,
        content_type="application/json",
        reply_to=reply_to,
        correlation_id=correlation_id,
    )
    ch.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(message),
        properties=props,
    )
    conn.close()

# ── 추천 응답 컨슈머 (reco.res만) ────────────────────────────────────────────
def _reco_callback(ch, method, properties, body):
    try:
        data = json.loads(body.decode("utf-8"))
        user_id = data.get("userId")
        if user_id:
            # Redis에 저장 (key: f"reco:{user_id}", TTL 5분)
            redis_client.setex(f"reco:{user_id}", 300, json.dumps(data))  ### 수정됨
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def _consume_reco_responses():
    params = pika.URLParameters(AMQP_URL)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    _declare_queue(ch, RECO_RES_QUEUE, None)
    ch.basic_consume(queue=RECO_RES_QUEUE, on_message_callback=_reco_callback, auto_ack=False)
    ch.start_consuming()

def consume_messages():
    threading.Thread(target=_consume_reco_responses, daemon=True).start()


# ── 인사이트(단방향) ────────────────────────────────────────────────────────
from datetime import datetime, timedelta

@router.post("/insights")
def create_insight_this_week(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    now = datetime.now()
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end   = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)

    insight = model.InsightEntity(user_id=current_user.user_id, status=model.InsightStatus.PENDING)
    db.add(insight); db.commit(); db.refresh(insight)

    memos = db.query(model.MemoEntity).filter(
        model.MemoEntity.user_id == current_user.user_id,
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

    # 인사이트 요청 발행(응답은 DB에 저장)
    payload = {"insightId": insight.insight_id, "userId": current_user.user_id, "logs": logs}
    _publish(INSIGHT_REQ_QUEUE, payload)
    return {"insightId": insight.insight_id, "status": insight.status}

@router.get("/insights")
def get_insight_status(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    insight = db.query(model.InsightEntity).filter(model.InsightEntity.user_id == current_user.user_id).first()
    now = datetime.now()
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end   = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
    memos = db.query(model.MemoEntity).filter(
        model.MemoEntity.user_id == current_user.user_id,
        model.MemoEntity.createdAt.between(start, end)
    ).all()
    insight = model.InsightEntity(user_id=current_user.user_id, status=model.InsightStatus.PENDING)
    db.add(insight); db.commit(); db.refresh(insight)

    memos = db.query(model.MemoEntity).filter(
        model.MemoEntity.user_id == current_user.user_id,
        model.MemoEntity.createdAt.between(start, end)
    ).all()
    memo_ids = [m.memo_id for m in memos]
    # 감정 가져오기
    emotions = db.query(model.EmotionEntity).filter(model.EmotionEntity.memo_id.in_(memo_ids)).all()
    emotion_labels = [e.emotion_label for e in emotions if e.emotion_label]
    # 레이블별 카운트 계산
    emotion_count = dict(Counter(emotion_labels))
    return {
        "id": insight.insight_id,
        "status": insight.status,
        "content": insight.content,
        "emotionCount": emotion_count   # 추가된 부분
    }

# ── 장소 추천(요청-응답: reco.req -> reco.res) ──────────────────────────────
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

    # LocationEntity와 조인해서 필터링
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

    locations = (
        db.query(model.LocationEntity)
        .filter(model.LocationEntity.location_id.in_(location_ids))
        .all()
    )

    candidates = [
    {
        "placeId":   loc.location_id,              # locationId → placeId
        "name":      loc.name,
        "category":  loc.category,
        "latitude":  float(loc.latitude or 0),    # lat → latitude
        "longitude": float(loc.longitude or 0),   # lon → longitude
    }
    for loc in locations
]

    # ── context ──

    # 1. recentEmotion (최근 작성한 메모의 감정 가져오기)
    recent_memo = (
        db.query(model.MemoEntity)
        .filter(model.MemoEntity.user_id == current_user.user_id)
        .order_by(model.MemoEntity.createdAt.desc())
        .first()
    )
    if recent_memo:
        emotions = (
            db.query(model.EmotionEntity)
            .filter(model.EmotionEntity.memo_id == recent_memo.memo_id)
            .all()
        )
        recent_emotion = [
            {"label": e.emotion_label, "score": e.emotion_score}
            for e in emotions
        ]
    else:
        recent_emotion = None

    # 2. favCategories (사용자가 많이 방문한 카테고리)
    user_memos = (
        db.query(model.MemoEntity)
        .join(model.LocationEntity, model.MemoEntity.location_id == model.LocationEntity.location_id)
        .filter(model.MemoEntity.user_id == current_user.user_id)
        .all()
    )
    cat_counts = Counter([m.location.category for m in user_memos if m.location and m.location.category])
    fav_categories = dict(cat_counts)

    # 3. scrapPlaceIds (스크랩한 장소)
    scrap_place_ids = [
        s.memo.location_id
        for s in db.query(model.MemoScrapEntity)
        .join(model.MemoEntity, model.MemoScrapEntity.memo_id == model.MemoEntity.memo_id)
        .filter(model.MemoScrapEntity.user_id == current_user.user_id)
        .all()
        if s.memo and s.memo.location_id
    ]

    # 4. followedUserIds (내가 팔로우한 사용자 ID)
    followed_user_ids = [
        f.following_id
        for f in db.query(model.FollowEntity)
        .filter(model.FollowEntity.follower_id == current_user.user_id, model.FollowEntity.is_approved == True)
        .all()
    ]

    # 5. placeSignals (장소별 긍정 비율, 팔로우한 유저의 긍정 개수)
    place_signals = []
    for loc in locations:
        memos_for_loc = (
            db.query(model.MemoEntity)
            .filter(model.MemoEntity.location_id == loc.location_id)
            .all()
        )
        if not memos_for_loc:
            pos_ratio = 0.0
            followed_pos_count = 0
        else:
            total = 0
            pos = 0
            followed_pos_count = 0
            for m in memos_for_loc:
                emotions = (
                    db.query(model.EmotionEntity)
                    .filter(model.EmotionEntity.memo_id == m.memo_id)
                    .all()
                )
                for e in emotions:
                    total += 1
                    if e.emotion_label == "긍정":  # DB에 저장된 값에 맞게 변경
                        pos += 1
                        if m.user_id in followed_user_ids:
                            followed_pos_count += 1
            pos_ratio = pos / total if total > 0 else 0.0

        place_signals.append(
            {
                "placeId": loc.location_id,
                "posRatio": round(pos_ratio, 2),
                "followedPositiveCount": followed_pos_count,
            }
        )

    # 최종 context
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
    _publish(RECO_REQ_QUEUE, payload, reply_to=RECO_RES_QUEUE, correlation_id=corr_id)

    return {
        "requestId": corr_id,
        "queued": True,
        "candidateCount": len(candidates)
    }

# ── 감정 분석(단방향) ────────────────────────────────────────────────────────
@router.post("/emotion_analysis/{memo_id}")
def emotion_analysis(memo_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    memo = db.query(model.MemoEntity).filter_by(memo_id=memo_id).first()
    if not memo:
        return {"error": "Memo not found"}
    payload = {"userId": current_user.user_id, "memoId": memo.memo_id, "content": memo.content}
    _publish(EMOTION_REQ_QUEUE, payload)
    return {"memo_id": memo.memo_id, "queued": True}

@router.get("/recommendations/{user_id}")  ### 수정됨
def get_recommendations(user_id: int):
    result = redis_client.get(f"reco:{user_id}")
    if not result:
        return {"status": "pending", "message": "No recommendations yet"}
    return json.loads(result)