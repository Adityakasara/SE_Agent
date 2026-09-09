from typing import List
from fastapi import APIRouter, HTTPException, status
from ..models.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

fake_db = [
    {"id": 1, "username": "alice", "email": "alice@example.com", "role": "admin"},
    {"id": 2, "username": "bob", "email": "bob@example.com", "role": "developer"},
]


@router.get("", response_model=List[UserResponse])
def get_users():
    return fake_db


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    # BUG: If email is None, user.email.lower() raises AttributeError (causing HTTP 500)
    # Proper fix should validate email presence or sanitize it safely
    normalized_email = user.email.lower()

    # Check for duplicate email
    for existing in fake_db:
        if existing["email"].lower() == normalized_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    new_user = {
        "id": len(fake_db) + 1,
        "username": user.username,
        "email": normalized_email,
        "role": user.role,
    }
    fake_db.append(new_user)
    return new_user
