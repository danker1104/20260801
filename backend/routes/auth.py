from fastapi import APIRouter

from auth import issue_anonymous_token
from config import AUTH_TOKEN_TTL_SECONDS

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/anonymous")
async def create_anonymous_session():
    token, user_id = issue_anonymous_token()
    return {"accessToken": token, "userId": user_id, "expiresIn": AUTH_TOKEN_TTL_SECONDS}
