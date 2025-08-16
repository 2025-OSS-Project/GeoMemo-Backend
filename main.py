from contextlib import asynccontextmanager
import threading
from fastapi import FastAPI
from api import auth, memo, user,system  # 예시
from fastapi.openapi.utils import get_openapi

from core import mq, s3

app = FastAPI()
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 실행할 코드
    threading.Thread(target=mq.consume_messages, daemon=True).start()
    yield
    # 서버 종료 시 실행할 코드 (필요하면)

app.router.lifespan_context = lifespan
# ✅ 먼저 라우터부터 등록
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(system.router)
app.include_router(memo.router)
app.include_router(s3.router)
app.include_router(mq.router)

# ✅ 그 다음 openapi 오버라이드
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
