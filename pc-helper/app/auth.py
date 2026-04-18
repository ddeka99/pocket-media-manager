from __future__ import annotations

from fastapi import HTTPException, status


def validate_token(
    expected_token: str,
    authorization: str | None = None,
    token: str | None = None,
) -> None:
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization.split(" ", 1)[1]
    else:
        provided = token

    if provided != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )
