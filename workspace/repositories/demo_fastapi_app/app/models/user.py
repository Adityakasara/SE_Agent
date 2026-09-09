from typing import Optional
from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    role: str = "developer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
