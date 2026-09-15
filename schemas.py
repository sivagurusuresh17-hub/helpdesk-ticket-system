from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "USER"


class UserLogin(BaseModel):
    email: EmailStr
    password: str