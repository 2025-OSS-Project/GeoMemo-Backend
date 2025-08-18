# exception.py
from enum import Enum
from fastapi import HTTPException

class ErrorCode(Enum):
    # Bad Request
    INVALID_INPUT = 1100

    # Unauthorized
    USER_NOT_FOUND = 2000
    EMPTY_TOKEN = 2001
    TOKEN_EXPIRED = 2002
    INVALID_TOKEN = 2003
    DENIED_PERMISSION = 2004
    INVALID_PASSWORD = 2005
    NICKNAME_DUPLICATE = 3001
    MEMO_UPDATE_DENIED_PERMISSION = 2005
 
    # Not Found
    SCRAP_NOT_FOUND = 4001
    MEMO_NOT_FOUND = 4002
    LOCATION_NOT_FOUND = 4003
    UPDATE_MEMO_NOT_FOUND = 4004

    # Internal Server Error
    UNEXPECTED_ERROR = 9000
    CONNECTION_ERROR = 9001
    MODEL_TIMEOUT = 9101

class OperatedException(HTTPException):
    def __init__(self, status_code: int, error_code: ErrorCode, detail: str):
        super().__init__(status_code=status_code, detail=detail)
        self.code = error_code