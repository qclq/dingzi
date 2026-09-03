from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    display_name: str
    role: str
    avatar_url: str | None = None


class TokenData(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int
    user_info: UserInfo


class AuthResponse(BaseModel):
    code: str = "SUCCESS"
    message: str
    data: TokenData
    trace_id: str


class MeResponse(BaseModel):
    user_id: int
    username: str
    display_name: str
    role: str
    avatar_url: str | None = None
    last_login: datetime | None = None


class MenuItem(BaseModel):
    name: str
    label: str
    path: str
    roles: list[str]
    children: list["MenuItem"] = []
