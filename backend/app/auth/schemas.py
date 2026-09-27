"""
Auth request/response schemas.

Login intentionally has no per-field validation beyond "these are
strings" — validating email format or password length on the *login*
path would let an attacker distinguish "malformed input" from "wrong
credentials" via response shape, undermining the same anti-enumeration
goal that the generic error message in the router is protecting.
Registration is where format/strength validation belongs.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    # Length floor only — this is a portfolio project's MVP, not a
    # password-strength-meter product. A real strength policy (breach
    # list checks, entropy estimation, etc.) is out of scope here.
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime
