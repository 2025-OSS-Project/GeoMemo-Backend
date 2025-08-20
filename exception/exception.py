# exception.py
from enum import Enum
from fastapi import HTTPException

class ErrorCode(Enum):
    # Bad Request
    INVALID_INPUT = 1100 # 필수 입력값 누락 (username, password 등), 유효하지 않은 이메일 형식
    USR_003 = 4003  # 비밀번호 형식 오류
    USR_006 = 4006  # 닉네임 길이 넘김
    USR_007 = 4007  # 전화번호 형식 오류

    # Conflict 409
    USR_004 = 4091  # 이미 존재하는 사용자명 (중복 아이디)
    USR_005 = 4092  # 이미 사용 중인 이메일

    # Internal Server Error 500
    USR_999 = 5999  # 서버 내부 오류 (예: DB 문제)
    # Unauthorized
    USER_NOT_FOUND = 2000
    EMPTY_TOKEN = 2001
    TOKEN_EXPIRED = 2002
    INVALID_TOKEN = 2003
    DENIED_PERMISSION = 2004
    INVALID_PASSWORD = 2005
    NICKNAME_DUPLICATE = 3001
    MEMO_UPDATE_DENIED_PERMISSION = 2006
 
    # Not Found
    SCRAP_NOT_FOUND = 4001
    MEMO_NOT_FOUND = 4002
    LOCATION_NOT_FOUND = 4003
    UPDATE_MEMO_NOT_FOUND = 4004
    INSIGHT_NOT_FOUND = 4005
    # Internal Server Error
    UNEXPECTED_ERROR = 9000
    CONNECTION_ERROR = 9001
    MODEL_TIMEOUT = 9101

class OperatedException(HTTPException):
    def __init__(self, status_code: int, error_code: ErrorCode, detail: str):
        super().__init__(status_code=status_code, detail=detail)
        self.code = error_code