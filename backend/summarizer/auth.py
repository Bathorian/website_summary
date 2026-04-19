import os
from typing import Any, Optional

import jwt
from clerk_backend_api.security import (
    TokenVerificationError,
    VerifyTokenOptions,
    verify_token_async,
)
from fastapi import HTTPException, Request
from pydantic import BaseModel


class CurrentUser(BaseModel):
    user_id: str
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


def _read_csv_env(name: str) -> Optional[list[str]]:
    raw_value = os.environ.get(name)
    if not raw_value:
        return None
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return values or None


def _read_audience_env() -> Optional[str | list[str]]:
    values = _read_csv_env("CLERK_JWT_AUDIENCE")
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return values


def _decode_unverified(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_aud": False,
            "verify_iss": False,
        },
        algorithms=["RS256", "HS256"],
    )


def _extract_email(payload: dict[str, Any]) -> Optional[str]:
    direct = payload.get("email") or payload.get("email_address")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    email_addresses = payload.get("email_addresses")
    if isinstance(email_addresses, list) and email_addresses:
        first = email_addresses[0]
        if isinstance(first, dict):
            value = first.get("email_address")
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def _extract_name(payload: dict[str, Any], key: str, fallback_key: str) -> Optional[str]:
    primary = payload.get(key)
    if isinstance(primary, str) and primary.strip():
        return primary.strip()

    secondary = payload.get(fallback_key)
    if isinstance(secondary, str) and secondary.strip():
        return secondary.strip()

    return None


def _build_user(payload: dict[str, Any]) -> CurrentUser:
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(status_code=401, detail="Token does not contain a valid user id")

    return CurrentUser(
        user_id=user_id,
        email=_extract_email(payload),
        username=_extract_name(payload, "username", "preferred_username"),
        first_name=_extract_name(payload, "first_name", "given_name"),
        last_name=_extract_name(payload, "last_name", "family_name"),
    )


def _guest_user() -> CurrentUser:
    return CurrentUser(user_id="guest_user", username="guest")


async def get_current_user(request: Request) -> CurrentUser:
    auth_header = request.headers.get("Authorization", "")
    clerk_secret_key = os.environ.get("CLERK_SECRET_KEY")

    if not auth_header:
        if not clerk_secret_key:
            return _guest_user()
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authorization header must use Bearer token")

    token = parts[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token is empty")

    if not clerk_secret_key:
        try:
            payload = _decode_unverified(token)
            return _build_user(payload)
        except Exception:
            return _guest_user()

    options = VerifyTokenOptions(
        secret_key=clerk_secret_key,
        audience=_read_audience_env(),
        authorized_parties=_read_csv_env("CLERK_AUTHORIZED_PARTIES"),
    )

    try:
        payload = await verify_token_async(token, options)
        return _build_user(payload)
    except TokenVerificationError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid or expired auth token: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Unable to authenticate user: {exc}") from exc
