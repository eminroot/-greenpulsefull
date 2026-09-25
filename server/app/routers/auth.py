"""Accounts, sessions and Google sign in.

Replaces Firebase Authentication. Error responses use short stable codes
(invalid_credentials, email_in_use, ...) which the app maps to its own
translated strings, so the wording stays in the app and works in every language
it ships.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete as sa_delete
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..deps import current_user
from ..models import RefreshToken, Site, User
from ..ratelimit import client_ip, login_limiter, signup_limiter
from ..schemas import (
    ChangePasswordIn,
    GoogleIn,
    LoginIn,
    RefreshIn,
    RegisterIn,
    TokenPair,
    UpdateMeIn,
    UserOut,
)
from ..security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    needs_rehash,
    normalise_email,
    password_problem,
    sha256,
    verify_password,
)

log = logging.getLogger("greenpulse.auth")
router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

_jwks_client: jwt.PyJWKClient | None = None


def _google_keys() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        # PyJWKClient caches the signing keys, so this is one network call every
        # few hours rather than one per sign in.
        _jwks_client = jwt.PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True)
    return _jwks_client


# --- throttling ------------------------------------------------------------
# Shared limiters live in app/ratelimit.py, which prunes itself. An earlier
# version kept a dict entry per (ip, email) pair forever, which is a slow memory
# leak an attacker can drive by guessing addresses.


def _login_key(request: Request, email: str) -> str:
    return f"{client_ip(request)}:{email}"


def _guard_login(key: str) -> None:
    if not login_limiter.check(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too_many_attempts",
            headers={"Retry-After": str(login_limiter.retry_after(key))},
        )


# --- helpers ---------------------------------------------------------------


async def _issue_tokens(
    session: AsyncSession, user: User, request: Request
) -> TokenPair:
    access, expires_in = create_access_token(user.id)
    raw_refresh, refresh_hash, expires_at = create_refresh_token()

    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=(request.headers.get("user-agent") or "")[:255] or None,
        )
    )
    await session.commit()

    return TokenPair(
        access_token=access,
        refresh_token=raw_refresh,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


async def _ensure_default_site(session: AsyncSession, user: User) -> None:
    """Every grower starts with one greenhouse, so a freshly paired node has
    somewhere to report before the farmer has configured anything."""
    exists = (
        await session.execute(select(Site.id).where(Site.user_id == user.id).limit(1))
    ).scalar_one_or_none()
    if exists:
        return
    session.add(Site(user_id=user.id, name="My greenhouse", slug="site-01"))
    await session.commit()


# --- endpoints -------------------------------------------------------------


@router.post("/register", response_model=TokenPair, status_code=201)
async def register(
    body: RegisterIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    if not signup_limiter.hit(client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too_many_attempts",
            headers={"Retry-After": str(signup_limiter.retry_after(client_ip(request)))},
        )

    email = normalise_email(body.email)

    problem = password_problem(body.password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)

    existing = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="email_in_use")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        display_name=(body.name or "").strip() or None,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await _ensure_default_site(session, user)

    return await _issue_tokens(session, user, request)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    email = normalise_email(body.email)
    key = _login_key(request, email)
    _guard_login(key)

    user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        login_limiter.record(key)
        # Same answer whether the address is unknown or the password is wrong.
        raise HTTPException(status_code=401, detail="invalid_credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="account_disabled")

    if user.password_hash and needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
        await session.commit()

    login_limiter.reset(key)
    await _ensure_default_site(session, user)
    return await _issue_tokens(session, user, request)


@router.post("/google", response_model=TokenPair)
async def google_sign_in(
    body: GoogleIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    """Verifies the id_token the app got from Google, then signs the user in.

    The token is checked against Google's published signing keys, its audience
    must be one of our own OAuth client ids and its issuer must be Google, so a
    token minted for some other app cannot be replayed here.
    """
    if not settings.google_audiences:
        raise HTTPException(status_code=501, detail="google_not_configured")

    try:
        signing_key = _google_keys().get_signing_key_from_jwt(body.id_token)
        claims = jwt.decode(
            body.id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.google_audiences,
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="google_token_invalid") from None

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise HTTPException(status_code=401, detail="google_token_invalid")
    if not claims.get("email_verified", False):
        raise HTTPException(status_code=401, detail="google_email_unverified")

    sub = claims["sub"]
    email = normalise_email(claims.get("email", ""))
    if not email:
        raise HTTPException(status_code=401, detail="google_token_invalid")

    user = (
        await session.execute(select(User).where(User.google_sub == sub))
    ).scalar_one_or_none()

    if user is None:
        # Link to an existing password account with the same verified address.
        user = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                google_sub=sub,
                display_name=(claims.get("name") or "").strip() or None,
            )
            session.add(user)
        else:
            user.google_sub = sub
        await session.commit()
        await session.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="account_disabled")

    await _ensure_default_site(session, user)
    return await _issue_tokens(session, user, request)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    """Rotates the refresh token: the presented one is revoked and a new pair is
    issued, so a stolen token stops working the moment the real client refreshes.

    Presenting an already revoked token means one of two things, and neither is
    normal: a replay, or a thief using a token the real client has since rotated
    past. Either way the safe response is to end every session for that account
    and make them sign in again.
    """
    token_hash = sha256(body.refresh_token.strip())
    row = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if row is None:
        raise HTTPException(status_code=401, detail="refresh_invalid")

    if row.revoked_at is not None:
        log.warning(
            "refresh token reuse for user %s; revoking every session", row.user_id
        )
        await session.execute(
            sa_delete(RefreshToken).where(RefreshToken.user_id == row.user_id)
        )
        await session.commit()
        raise HTTPException(status_code=401, detail="refresh_invalid")

    expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=401, detail="refresh_expired")

    user = await session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="refresh_invalid")

    row.revoked_at = now

    # Rotation leaves a spent row behind on every refresh, so tidy this
    # account's dead ones as we go rather than growing the table forever.
    await session.execute(
        sa_delete(RefreshToken).where(
            RefreshToken.user_id == row.user_id,
            RefreshToken.id != row.id,
            or_(
                RefreshToken.expires_at <= now,
                RefreshToken.revoked_at < now - timedelta(days=2),
            ),
        )
    )
    await session.commit()
    return await _issue_tokens(session, user, request)


@router.post("/logout", status_code=204)
async def logout(
    body: RefreshIn,
    session: AsyncSession = Depends(get_session),
) -> None:
    token_hash = sha256(body.refresh_token.strip())
    row = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
    ).scalar_one_or_none()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        await session.commit()


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: UpdateMeIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    if body.name is not None:
        user.display_name = body.name.strip() or None
    await session.commit()
    await session.refresh(user)
    return UserOut.model_validate(user)


@router.post("/me/password", status_code=204)
async def change_password(
    body: ChangePasswordIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    # An account created through Google has no password yet, so it can set one
    # without proving the old one.
    if user.password_hash:
        if not body.current_password or not verify_password(
            body.current_password, user.password_hash
        ):
            raise HTTPException(status_code=401, detail="invalid_credentials")

    problem = password_problem(body.new_password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)

    user.password_hash = hash_password(body.new_password)
    # Changing the password ends every other session.
    await session.execute(
        sa_delete(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    await session.commit()


@router.delete("/me", status_code=204)
async def delete_me(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Removes the account and everything attached to it.

    Sites, devices, captures, readings and events all cascade. Stored images are
    removed with the site, so nothing of the grower's is left behind.
    """
    sites = (
        await session.execute(select(Site).where(Site.user_id == user.id))
    ).scalars().all()
    for site in sites:
        site_dir = settings.data_dir / site.id
        if site_dir.is_dir():
            for path in sorted(site_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                else:
                    path.rmdir()
            site_dir.rmdir()

    await session.delete(user)
    await session.commit()
