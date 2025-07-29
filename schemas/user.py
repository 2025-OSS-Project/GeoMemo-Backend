from pydantic import BaseModel, EmailStr
from typing import Optional, Dict

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

class PasswordUpdateResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, str]]
    error: Optional[str]

#닉네임 변경 스키마
class NicknameUpdateRequest(BaseModel):
    nickname: str

class NicknameUpdateResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, str]]
    error: Optional[str]

#회원탈퇴 스키마
class DeleteUserResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, int]]
    error: Optional[str]