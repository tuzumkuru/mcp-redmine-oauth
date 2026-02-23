"""Redmine OAuth provider for FastMCP.

Bridges FastMCP's OAuthProxy to Redmine 6.1's native OAuth 2.0 provider.
Redmine issues opaque tokens (not JWTs), so we verify them by calling
Redmine's /users/current.json endpoint.

Granted scopes are captured from the token-exchange response via
_extract_upstream_claims and stored in a shared scope_store, so that
verify_token can populate AccessToken.scopes with real values.
"""

from __future__ import annotations

from typing import Any

import httpx
from key_value.aio.protocols import AsyncKeyValue
from pydantic import AnyHttpUrl

from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.utilities.logging import get_logger

from mcp_redmine_oauth.scopes import get_registered_scopes

logger = get_logger(__name__)


class RedmineTokenVerifier(TokenVerifier):
    """Verify Redmine OAuth tokens by calling /users/current.json."""

    def __init__(
        self,
        *,
        redmine_url: str,
        timeout_seconds: int = 10,
        scope_store: dict[str, list[str]],
    ):
        super().__init__()
        self.redmine_url = redmine_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._scope_store = scope_store

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{self.redmine_url}/users/current.json",
                    headers={"Authorization": f"Bearer {token}"},
                )

                if response.status_code != 200:
                    logger.debug(
                        "Redmine token verification failed: %d",
                        response.status_code,
                    )
                    return None

                data = response.json()
                user = data.get("user", {})

                # Use scopes captured during token exchange; fall back to all registered scopes
                # (covers token-refresh case where _extract_upstream_claims wasn't called)
                granted_scopes = self._scope_store.get(token, get_registered_scopes())

                return AccessToken(
                    token=token,
                    client_id=str(user.get("id", "unknown")),
                    scopes=granted_scopes,
                    expires_at=None,
                    claims={
                        "sub": str(user.get("id")),
                        "login": user.get("login"),
                        "firstname": user.get("firstname"),
                        "lastname": user.get("lastname"),
                        "mail": user.get("mail"),
                    },
                )

        except httpx.RequestError as e:
            logger.debug("Failed to verify Redmine token: %s", e)
            return None


class RedmineProvider(OAuthProxy):
    """OAuth provider connecting FastMCP to a Redmine 6.1+ instance.

    Usage:
        auth = RedmineProvider(
            redmine_url="https://redmine.example.com",
            client_id="your-client-id",
            client_secret="your-client-secret",
            base_url="http://localhost:8000",
        )
        mcp = FastMCP("Redmine MCP", auth=auth)
    """

    def __init__(
        self,
        *,
        redmine_url: str,
        client_id: str,
        client_secret: str,
        base_url: AnyHttpUrl | str,
        scopes: list[str] | None = None,
        redirect_path: str | None = None,
        allowed_client_redirect_uris: list[str] | None = None,
        client_storage: AsyncKeyValue | None = None,
        jwt_signing_key: str | bytes | None = None,
        require_authorization_consent: bool = False,
    ):
        redmine_url = redmine_url.rstrip("/")

        self._scope_store: dict[str, list[str]] = {}
        token_verifier = RedmineTokenVerifier(
            redmine_url=redmine_url,
            scope_store=self._scope_store,
        )

        extra_authorize_params = {"scope": " ".join(scopes)} if scopes else {}

        super().__init__(
            upstream_authorization_endpoint=f"{redmine_url}/oauth/authorize",
            upstream_token_endpoint=f"{redmine_url}/oauth/token",
            upstream_client_id=client_id,
            upstream_client_secret=client_secret,
            token_verifier=token_verifier,
            base_url=base_url,
            issuer_url=base_url,
            redirect_path=redirect_path,
            allowed_client_redirect_uris=allowed_client_redirect_uris,
            client_storage=client_storage,
            jwt_signing_key=jwt_signing_key,
            require_authorization_consent=require_authorization_consent,
            extra_authorize_params=extra_authorize_params,
        )

        logger.debug(
            "Initialized Redmine OAuth provider for %s", redmine_url
        )

    async def _extract_upstream_claims(
        self, idp_tokens: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Capture granted scopes from Redmine's token-exchange response."""
        access_token = idp_tokens.get("access_token", "")
        scope_str = idp_tokens.get("scope", "")
        if access_token and scope_str:
            self._scope_store[access_token] = scope_str.split()
            logger.debug(
                "Captured scopes for token …%s: %s", access_token[-6:], scope_str
            )
        return None  # Don't embed extra claims in the FastMCP JWT
