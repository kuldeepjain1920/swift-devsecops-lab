"""
Phase 1 auth stub — NOT real authentication or authorization.
This exists only so api/routes.py has a consistent interface to call,
so that when Phase 2 wires in Keycloak (OAuth2/OIDC) + OPA (RBAC/ABAC),
only this file changes — routes.py doesn't need to know the difference.
"""

def get_current_user() -> dict:
    # Placeholder — always returns a fake authenticated user.
    # Phase 2 replaces this with real OIDC token validation.
    return {"user_id": "stub-user", "roles": ["operator"]}
