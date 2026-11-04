from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TransactionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0)
    transaction_type: str
    category: str = "Other"
    transaction_date: date
    description: str | None = None
    source: str = "manual"

    @field_validator("transaction_type")
    @classmethod
    def valid_type(cls, value):
        if value not in {"Income", "Expense"}:
            raise ValueError("transaction_type must be Income or Expense")
        return value

class TransactionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    amount: float | None = Field(default=None, gt=0)
    transaction_type: str | None = None
    category: str | None = None
    transaction_date: date | None = None
    description: str | None = None

    @field_validator("transaction_type")
    @classmethod
    def valid_type(cls, value):
        if value is not None and value not in {"Income", "Expense"}:
            raise ValueError("transaction_type must be Income or Expense")
        return value

class TransactionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    amount: float
    transaction_type: str
    category: str
    transaction_date: date
    description: str | None
    source: str
    model_config = ConfigDict(from_attributes=True)
