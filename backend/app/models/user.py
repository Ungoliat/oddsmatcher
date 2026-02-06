from pydantic import BaseModel
from typing import Literal


Role = Literal["free", "pro", "admin"]


class User(BaseModel):
    username: str
    role: Role
    disabled: bool = False
    hashed_password: str


class UserPublic(BaseModel):
    username: str
    role: Role
    disabled: bool = False
