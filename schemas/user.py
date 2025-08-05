from pydantic import BaseModel, EmailStr
from typing import Optional, Dict

from schemas.response import APIResponse

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    nickname: str
    phone: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

#비밀번호 변경 스키마
class PasswordUpdateRequest(BaseModel):
    password: str

PasswordUpdateResponse = APIResponse[Optional[Dict[str, str]]]

#닉네임 변경 스키마
class NicknameUpdateRequest(BaseModel):
    nickname: str

NicknameUpdateResponse = APIResponse[Optional[Dict[str, str]]]

#회원탈퇴 스키마
UserDeleteResponse = APIResponse[Optional[Dict[str, int]]]
    