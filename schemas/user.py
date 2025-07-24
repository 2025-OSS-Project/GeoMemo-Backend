from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    nickname: str
    phone: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
