# src/auth/oidc.py
# Validates OAuth2/OIDC bearer tokens issued by Keycloak. Fetches Keycloak's
# public signing keys (JWKS) once and caches them, then verifies each incoming
# request's JWT signature, expiry, issuer, and audience against them.

import os
import time
import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# --- Configuration (pulled from environment, not hardcoded) ---
# KC_BASE_URL: Keycloak's endpoint reachable from swift-lab-vm.
#   Currently HTTP on port 8080 — a DELIBERATE, TEMPORARY choice.
#   Keycloak's start-dev mode has no working HTTPS listener without an
#   explicitly configured keystore, so real TLS here is deferred to
#   Phase 3 (PKI, certificates & machine identity). The firewall rule
#   allow_app_vpc_to_keycloak was updated to match (8080, not 8443).
#   TODO(Phase 3): switch back to https://.../8443 once Keycloak has a
#   real certificate, and re-enable verify=True below.
KC_REALM = os.environ["KC_REALM"]  # e.g. swift-devsecops-lab
KC_CLIENT_ID = os.environ["KC_CLIENT_ID"]  # e.g. swift-payment-api

KC_BASE_URL = os.environ["KC_BASE_URL"]  # e.g. http://10.20.0.2:8080 — used for actual connectivity
ISSUER = f"http://localhost:8080/realms/{KC_REALM}"  # hardcoded to match the token's real iss claim
JWKS_URL = f"{KC_BASE_URL}/realms/{KC_REALM}/protocol/openid-connect/certs"  # built from KC_BASE_URL, NOT ISSUER

# --- JWKS caching ---
# Keycloak's signing keys rarely change, so we cache them in memory rather
# than fetching on every single request. Cache expires after 1 hour as a
# safety net in case Keycloak rotates its keys.
_jwks_cache: dict = {}
_jwks_cache_time: float = 0
_JWKS_CACHE_TTL_SECONDS = 3600

security = HTTPBearer()


def _get_jwks() -> dict:
    """Fetch (and cache) Keycloak's public signing keys."""
    global _jwks_cache, _jwks_cache_time

    if _jwks_cache and (time.time() - _jwks_cache_time) < _JWKS_CACHE_TTL_SECONDS:
        return _jwks_cache

    # verify=False: Keycloak's start-dev mode uses a self-signed cert on 8443.
    # This is a deliberate, flagged lab-only compromise — Phase 3 (PKI/mTLS)
    # replaces this with a real trusted certificate, at which point this
    # should become verify=True (or point at a custom CA bundle).
    # response = httpx.get(JWKS_URL, verify=False, timeout=5.0)
    
    # Plain HTTP for now (see KC_BASE_URL comment above) — no TLS verification
    # needed since there's no cert involved yet. This becomes verify=True
    # (or a custom CA bundle) once Phase 3 issues Keycloak a real certificate
    # and this switches back to HTTPS.
    response = httpx.get(JWKS_URL, timeout=5.0)
    response.raise_for_status()

    _jwks_cache = response.json()
    _jwks_cache_time = time.time()
    return _jwks_cache


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    FastAPI dependency: validates the bearer token on an incoming request.
    Returns the decoded token claims (username, roles, etc.) if valid,
    otherwise raises a 401.
    """
    token = credentials.credentials

    try:
        jwks = _get_jwks()
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],  # Keycloak's default signing algorithm
            audience=KC_CLIENT_ID,
            issuer=ISSUER,
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims


# --- RBAC: role-based authorization, built on top of the already-validated token ---
def get_roles(payload: dict) -> list[str]:
    """
    Extract realm roles from a decoded Keycloak token.
    Keycloak puts realm-level roles (the ones you created: payment-initiator,
    payment-approver, payment-auditor) under realm_access.roles.
    Client-specific roles would instead live under resource_access.<client_id>.roles —
    not used here since we created these as realm roles.
    """
    realm_access = payload.get("realm_access", {})  # {} if claim missing, avoids KeyError
    return realm_access.get("roles", [])


def require_role(*allowed_roles: str):
    """
    Dependency FACTORY — not a dependency itself.
    Call it with the roles you want to allow, e.g. Depends(require_role("payment-approver")),
    and it returns a dependency function FastAPI can actually inject.

    Why a factory: FastAPI's Depends() needs a callable with no *required* custom args at
    call time, so we bind the allowed_roles via closure instead of passing them at request time.
    """
    def role_checker(payload: dict = Depends(validate_token)) -> dict:
        # validate_token already ran signature/issuer/audience checks — this
        # only adds the authorization layer on top of that authenticated identity.
        user_roles = get_roles(payload)

        # any() short-circuits — fine for our small role sets
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {allowed_roles}. Token has: {user_roles}",
            )
        return payload  # pass the payload through, in case the route wants it too

    return role_checker

# --- ABAC: attribute-based authorization via OPA ---

OPA_URL = os.environ.get("OPA_URL", "http://opa:8181")  # container-name resolution via swift-lab-net

async def check_opa_authorization(action: str, roles: list[str], amount: float) -> bool:
    """
    Queries OPA's REST API for an authorization decision, rather than
    encoding the amount-threshold logic directly in Python. This is the
    core ABAC pattern: the decision LOGIC lives in Rego (policy-as-code),
    the app just supplies the relevant attributes (action, roles, amount)
    and asks "is this allowed?"
    """

    opa_input = {
        "input": {
            "action": action,
            "roles": roles,
            "amount": amount,
        }
    }

    async with httpx.AsyncClient() as client:
        # OPA's data API path mirrors the Rego package name:
        # package payment.authz -> /v1/data/payment/authz
        response = await client.post(f"{OPA_URL}/v1/data/payment/authz", json=opa_input, timeout=5.0)
        response.raise_for_status()
        result = response.json()

    # OPA wraps every result in {"result": {...}}. If "allow" is missing
    # entirely (e.g. a malformed policy), default to False — fail closed.
    return result.get("result", {}).get("allow", False)
