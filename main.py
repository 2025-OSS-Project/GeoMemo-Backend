from contextlib import asynccontextmanager
import threading
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from api import auth, memo, user, system
from fastapi.openapi.utils import get_openapi
from core import mq, s3
from exception.handler import set_error_handlers
from api.scheduler import daily_job  # daily_job 함수 import

app = FastAPI()
set_error_handlers(app)

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시
    threading.Thread(target=mq.consume_messages, daemon=True).start()
    scheduler.add_job(daily_job, "interval", minutes=1)  # 1분마다 실행

 # 테스트용 10초 간격
    scheduler.start()
    print("스케줄러 시작")
    yield
    # 서버 종료 시
    scheduler.shutdown()
    print("스케줄러 종료")

# lifespan 컨텍스트 등록
app.router.lifespan_context = lifespan

# 라우터 등록
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(system.router)
app.include_router(memo.router)
app.include_router(s3.router)
app.include_router(mq.router)

# OpenAPI 커스터마이징
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="GeoMemo API",
        version="1.0.0",
        description="GeoMemo 백엔드 API 문서입니다.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
