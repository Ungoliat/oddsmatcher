from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.models.user import User, Role

# 🔐 Cambia esto por una cadena larga y secreta (luego la pondremos en .env)
SECRET_KEY = "CHANGE_ME__LONG_RANDOM_SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# 👇 Usuarios en memoria (MVP). Luego lo cambiamos a DB.
# Passwords: free123 / pro123 / admin123
_fake_users_db: Dict[str, User] = {
    "andy": User(username="andy", role="free", hashed_password=pwd_context.hash("free123")),
    "pro": User(username="pro", role="pro", hashed_password=pwd_context.hash("pro123")),
    "admin": User(username="admin", role="admin", hashed_password=pwd_context.hash("admin123")),
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

from app.services.user_repo import get_user_row, upsert_user

# ... el resto igual ...

def get_user(username: str) -> Optional[User]:
    row = get_user_row(username)
    if not row:
        return None

    return User(
        username=row["username"],
        role=row["role"],
        disabled=bool(row["disabled"]),
        hashed_password=row["hashed_password"],
    )


def authenticate_user(username: str, password: str) -> Optional[User]:
    user = get_user(username)
    if not user:
        return None
    if user.disabled:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(subject: str, role: Role, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def ensure_default_users() -> None:
    # Solo crea si no existen (upsert hace update también, pero aquí da igual)
    # Passwords: free123 / pro123 / admin123
    upsert_user("andy", pwd_context.hash("free123"), "free", disabled=False)
    upsert_user("pro", pwd_context.hash("pro123"), "pro", disabled=False)
    upsert_user("admin", pwd_context.hash("admin123"), "admin", disabled=False)
