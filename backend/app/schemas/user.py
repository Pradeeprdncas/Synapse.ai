from pydantic import BaseModel, Field, field_validator
from typing import Optional


class UserCreate(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=7, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("A valid email address is required")
        return value


class UserLogin(BaseModel):
    email: str
    password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    email: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(default=None, min_length=7, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_optional_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("A valid email address is required")
        return value


class AdminUserCreate(UserCreate):
    role: str = "MEMBER"
    send_email: bool = True

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        value = value.upper()
        if value not in {"ADMIN", "MEMBER"}:
            raise ValueError("Application role must be ADMIN or MEMBER")
        return value


class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=7, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_admin_email(cls, value: Optional[str]) -> Optional[str]:
        return ProfileUpdate.normalize_optional_email(value)

    @field_validator("role")
    @classmethod
    def valid_optional_role(cls, value: Optional[str]) -> Optional[str]:
        return AdminUserCreate.valid_role(value) if value else value


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True
