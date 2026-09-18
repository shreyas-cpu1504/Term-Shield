import asyncio
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus, urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    OAuthExchangeRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])

bearer_scheme = HTTPBearer(auto_error=False)

# Short-lived, single-use exchange codes for secure OAuth callback handoff
_oauth_exchange_codes: dict[str, dict] = {}
_oauth_exchange_lock = asyncio.Lock()


async def create_oauth_exchange_code(user_id: str) -> str:
    """Create an opaque, single-use, 60-second exchange code for OAuth handoff."""
    code = secrets.token_urlsafe(32)
    now = time.time()
    async with _oauth_exchange_lock:
        # Purge expired codes
        expired_keys = [k for k, v in _oauth_exchange_codes.items() if v["expires_at"] < now]
        for k in expired_keys:
            _oauth_exchange_codes.pop(k, None)

        _oauth_exchange_codes[code] = {
            "user_id": user_id,
            "expires_at": now + 60.0,
        }
    return code


async def consume_oauth_exchange_code(code: str) -> str | None:
    """Atomically consume and invalidate an exchange code, returning the associated user_id."""
    now = time.time()
    async with _oauth_exchange_lock:
        entry = _oauth_exchange_codes.pop(code, None)

    if not entry or entry["expires_at"] < now:
        return None
    return entry["user_id"]


def generate_oauth_state(provider: str) -> str:
    settings = get_settings()
    secret = settings.jwt_secret_key or "term-shield-oauth-state-secret"
    payload = {
        "provider": provider,
        "nonce": secrets.token_urlsafe(16),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_oauth_state(state: str, expected_provider: str) -> bool:
    settings = get_settings()
    secret = settings.jwt_secret_key or "term-shield-oauth-state-secret"
    try:
        payload = jwt.decode(state, secret, algorithms=["HS256"])
        return payload.get("provider") == expected_provider
    except Exception:
        return False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Return the authenticated user from the JWT bearer token."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user."""

    result = await db.execute(
        select(User).where(User.email == request.email.lower())
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        email=request.email.lower(),
        full_name=request.full_name.strip(),
        hashed_password=hash_password(request.password),
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    await db.flush()

    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a JWT."""

    result = await db.execute(
        select(User).where(User.email == request.email.lower())
    )

    user = result.scalar_one_or_none()

    if user is None or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user."""

    return UserResponse.model_validate(current_user)


@router.get("/providers")
async def get_auth_providers():
    """Return configured OAuth providers."""
    settings = get_settings()
    return {
        "google": {
            "enabled": bool(settings.google_client_id and settings.google_client_secret),
            "login_url": "/api/v1/auth/google/login",
        },
    }


@router.get("/google/login")
async def google_login():
    """Redirect to Google's OAuth 2.0 authorization endpoint."""
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured on the server. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the environment.",
        )

    redirect_uri = settings.google_redirect_uri or "http://127.0.0.1:8000/api/v1/auth/google/callback"
    state = generate_oauth_state("google")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback, exchange code, link or create user, and issue Term Shield JWT."""
    settings = get_settings()
    frontend_url = settings.frontend_url.rstrip("/")

    if error:
        return RedirectResponse(f"{frontend_url}/?error={quote_plus(error)}")

    if not code or not state or not verify_oauth_state(state, "google"):
        return RedirectResponse(f"{frontend_url}/?error=Invalid+or+expired+OAuth+state")

    redirect_uri = settings.google_redirect_uri or "http://127.0.0.1:8000/api/v1/auth/google/callback"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            if token_resp.status_code != 200:
                return RedirectResponse(f"{frontend_url}/?error=Failed+to+exchange+Google+authorization+code")

            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                return RedirectResponse(f"{frontend_url}/?error=Missing+Google+access+token")

            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_resp.status_code != 200:
                return RedirectResponse(f"{frontend_url}/?error=Failed+to+retrieve+Google+user+profile")

            user_info = userinfo_resp.json()
            if not user_info.get("email_verified", True):
                return RedirectResponse(f"{frontend_url}/?error=Google+account+email+is+not+verified")

            email = user_info.get("email")
            if not email:
                return RedirectResponse(f"{frontend_url}/?error=Google+profile+did+not+provide+an+email")

            name = user_info.get("name") or email.split("@")[0]

    except Exception as ex:
        return RedirectResponse(f"{frontend_url}/?error={quote_plus(f'Google OAuth error: {str(ex)}')}")

    # Account linking / User creation with existing Term Shield model
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email.lower(),
            full_name=name.strip(),
            hashed_password=None,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()
    else:
        if not user.is_active:
            return RedirectResponse(f"{frontend_url}/?error=User+account+is+inactive")
        if not user.is_verified:
            user.is_verified = True
            await db.flush()

    exchange_code = await create_oauth_exchange_code(user.id)
    return RedirectResponse(f"{frontend_url}/?oauth_code={exchange_code}")



@router.post(
    "/oauth/exchange",
    response_model=TokenResponse,
)
async def exchange_oauth_code(
    request: OAuthExchangeRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a short-lived, single-use OAuth code for a Term Shield JWT."""
    code = request.code.strip() if request.code else ""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing exchange code",
        )

    user_id = await consume_oauth_exchange_code(code)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired exchange code",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


