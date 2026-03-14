from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)
    name: str = Field(..., min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)


class AuthUserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
