from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    status: int
    message: str


class DataResponse(BaseResponse, Generic[T]):
    data: T



class PriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserResponse(UserBase):
    id: int
    balance: float = 1000000.0
    is_favorite: bool = False
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None


class LoginResponse(BaseResponse):
    data: Token
    access_token: str
    token_type: str = "bearer"



class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_completed: bool = False
    priority: PriorityEnum = PriorityEnum.MEDIUM
    due_date: datetime | None = None


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_completed: bool | None = None
    priority: PriorityEnum | None = None
    due_date: datetime | None = None


class TodoResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    is_completed: bool
    priority: str
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BiometricCredentialCreate(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128)
    device_name: str | None = Field(default=None, max_length=255)
    public_key: str = Field(..., min_length=1, max_length=4096)
    key_algorithm: str = Field(default="ECDSA_P256_SHA256", min_length=1, max_length=50)


class BiometricCredentialStatusResponse(BaseModel):
    credential_id: str
    status: str


class BiometricCredentialResponse(BaseModel):
    credential_id: str
    device_id: str
    device_name: str | None
    key_algorithm: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BiometricChallengeRequest(BaseModel):
    credential_id: str = Field(..., min_length=1, max_length=36)


class BiometricChallengeResponse(BaseModel):
    challenge_id: str
    challenge: str
    expires_at: datetime


class BiometricVerifyRequest(BaseModel):
    challenge_id: str = Field(..., min_length=1, max_length=36)
    credential_id: str = Field(..., min_length=1, max_length=36)
    signature: str = Field(..., min_length=1, max_length=1024)


class TransferCreate(BaseModel):
    user_id: int = Field(..., description="Recipient user ID")
    nominal: float = Field(..., gt=0, description="Transfer nominal amount")
    transaction_type: str = Field(..., min_length=1, max_length=100)
    transaction_purpose: str = Field(..., min_length=1, max_length=255)


class TransferResponse(BaseModel):
    id: int
    sender_id: int
    user_id: int
    nominal: float
    transaction_type: str
    transaction_purpose: str
    sender_balance: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


