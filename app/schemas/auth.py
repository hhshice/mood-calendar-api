from pydantic import BaseModel, field_validator


class UserInfo(BaseModel):
    id: int
    nickname: str
    avatar: str

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("登录 code 不能为空")
        return v.strip()


class LoginResponse(BaseModel):
    token: str
    user: UserInfo


class UpdateUserRequest(BaseModel):
    nickname: str | None = None
    avatar: str | None = None
