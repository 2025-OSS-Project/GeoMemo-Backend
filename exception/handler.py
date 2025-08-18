# handler.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from exception.exception import OperatedException, ErrorCode

def set_error_handlers(app: FastAPI):

    # 클라이언트의 요청 처리에 따라 발생한 예외는 OperatedException로 처리
    @app.exception_handler(OperatedException)
    async def operated_exception_handler(request: Request, exc: OperatedException):
        return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code.value,
            "reason": exc.code.name,
            "message": exc.detail
        }
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
        status_code=422,
        content={
            "code": ErrorCode.INVALID_INPUT.value,
            "detail": exc.errors(),
            "body": exc.body
        },
    )
    # 그 외 요청을 처리하다가 서버에서 예상치 못한 예외가 발생한 경우
    @app.exception_handler(Exception)
    async def server_side_exception_handler(request: Request, exc: Exception):
        # error response
        return JSONResponse(
            status_code=500,
            content={"code": ErrorCode.UNEXPECTED_ERROR.value, "reason": "UNEXPECTED_ERROR", "message": str(exc)}
        )
