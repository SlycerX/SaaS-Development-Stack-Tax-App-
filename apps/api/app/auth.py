import os
from typing import Protocol

import jwt
from fastapi import HTTPException


class TokenVerifier(Protocol):
    def verify(self, token: str) -> dict:
        """Return verified claims or raise HTTPException."""


class CognitoTokenVerifier:
    """Verifies a Cognito access token. The pool settings come from the environment."""

    def __init__(self) -> None:
        self.region = os.environ["COGNITO_REGION"]
        self.pool_id = os.environ["COGNITO_USER_POOL_ID"]
        self.client_id = os.environ["COGNITO_APP_CLIENT_ID"]
        self.issuer = f"https://cognito-idp.{self.region}.amazonaws.com/{self.pool_id}"
        jwks_url = f"{self.issuer}/.well-known/jwks.json"
        self.jwks_client = jwt.PyJWKClient(jwks_url)

    def verify(self, token: str) -> dict:
        key = self.jwks_client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=self.issuer,
            options={"require": ["exp", "iss", "token_use"]},
        )


def cognito_configured() -> bool:
    return all(
        os.getenv(name)
        for name in ("COGNITO_REGION", "COGNITO_USER_POOL_ID", "COGNITO_APP_CLIENT_ID")
    )


def verifier_from_env() -> TokenVerifier:
    if not cognito_configured():
        raise HTTPException(status_code=503, detail="Cognito is not configured")
    return CognitoTokenVerifier()


def require_user(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return verifier_from_env().verify(token)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
