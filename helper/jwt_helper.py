import jwt
from datetime import datetime, timedelta
import os

JWT_SECRET = os.getenv("JWT_SECRET_KEY")
JWT_ALGO = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_MIN = int(os.getenv("JWT_EXPIRE_MINUTES", 25))


# =========================
# TOKEN GENERATE
# =========================
def generate_token(payload: dict):
    payload = payload.copy()
    
    exp_time = datetime.utcnow() + timedelta(minutes=JWT_EXP_MIN)

    payload["exp"] = exp_time
    payload["iat"] = datetime.utcnow()

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    return token,int(exp_time.timestamp())


# =========================
# TOKEN VERIFY / DECODE
# =========================
def verify_token(token: str):
    """
    Returns:
        dict → valid token payload
        None → invalid / expired token
    """
    try:
        decoded = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGO]
        )
        return decoded

    except jwt.ExpiredSignatureError:
        return None

    except jwt.InvalidTokenError:
        return None
