import os
import base64
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse
from cryptography.hazmat.primitives import serialization

from src.models.message import PaymentMessage, MessageStatus
from src.api.validation import validate_message, ValidationError
from src.api.routing import route_message
from src.api.audit import log_transition
from src.crypto.signing import sign_message
from src.crypto.encryption import encrypt_field
from src.auth.oidc import validate_token, require_role, get_roles, check_opa_authorization

import xml.etree.ElementTree as ET

# SAML XML uses namespaced tags — these prefixes let ElementTree find
# elements like <saml:NameID> without spelling out the full URI every time.
SAML_NS = {
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
}

router = APIRouter()

# Load the signing key once at import time rather than per-request —
# reading from disk on every call would be wasteful and the key doesn't
# change during the process lifetime.
_SIGNING_KEY_PATH = os.environ["SIGNING_KEY_PATH"]
with open(_SIGNING_KEY_PATH, "rb") as f:
    _PRIVATE_KEY = serialization.load_pem_private_key(f.read(), password=None)

# AES key is stored as base64 text in .env — decode once at import time,
# same reasoning as the signing key above.
_AES_KEY = base64.b64decode(os.environ["AES_KEY"])

# In-memory store for Phase 1 only — no real database yet. Good enough
# to demonstrate the flow; real persistence would come in a later phase.
_MESSAGES: dict[str, PaymentMessage] = {}

@router.post("/messages", status_code=201)
async def submit_message(msg: PaymentMessage, claims: dict = Depends(require_role("payment-initiator"))):
    # Real OIDC token validation — claims now holds the decoded JWT
    # (username, roles, etc.) from a genuine Keycloak-issued bearer token.
    # Replaces the Phase 1 stub_auth call site.
    # RBAC: only payment-initiator role may submit a new payment message.
    # RBAC (require_role) already confirmed payment-initiator role is present.
    # ABAC now checks whether THIS SPECIFIC request (based on its amount) is
    # allowed given the caller's full role set — not just the one role RBAC required.
    user_roles = get_roles(claims)
    allowed = await check_opa_authorization(
        action="submit",
        roles=user_roles,
        amount=float(msg.amount),  # msg.amount is a Decimal; OPA/JSON needs a plain number
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"OPA policy denied: amount {msg.amount} requires payment-approver role for amounts over threshold",
        )

    # Idempotency check — if this message_id was already submitted,
    # return its current state instead of reprocessing it. Mirrors
    # duplicate-message detection on the real FIN network.
    if msg.message_id in _MESSAGES:
        return _MESSAGES[msg.message_id]

    _MESSAGES[msg.message_id] = msg

    # --- Validate ---
    try:
        validate_message(msg)
        msg.status = MessageStatus.VALIDATED
        log_transition(msg.message_id, "submitted", "validated")
    except ValidationError as e:
        msg.status = MessageStatus.NACKED
        log_transition(msg.message_id, "submitted", "nacked", reason=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    # --- Sign ---
    # Sign the canonical message bytes BEFORE encryption, so a downstream
    # verifier can check integrity without needing to decrypt first.
    payload_bytes = msg.model_dump_json().encode()
    signature = sign_message(payload_bytes, _PRIVATE_KEY)
    msg.status = MessageStatus.SIGNED
    log_transition(msg.message_id, "validated", "signed")

    # --- Encrypt sensitive field ---
    ciphertext, nonce = encrypt_field(msg.account_number, _AES_KEY)
    # Overwrite plaintext with the encrypted form; the raw account number
    # should not persist in memory/logs beyond this point.
    msg.account_number = base64.b64encode(ciphertext).decode()

    # --- Route ---
    delivered = route_message(msg)
    if delivered:
        msg.status = MessageStatus.ACKED
        log_transition(msg.message_id, "signed", "acked")
    else:
        msg.status = MessageStatus.NACKED
        log_transition(msg.message_id, "signed", "nacked", reason="routing failed")

    return msg


@router.get("/messages/{message_id}")
def get_message(message_id: str):
    # Simple lookup endpoint — lets a client check status after submission
    # without needing to resubmit.
    if message_id not in _MESSAGES:
        raise HTTPException(status_code=404, detail="message not found")
    return _MESSAGES[message_id]

# --- OIDC test endpoint (Phase 2) ---
@router.get("/whoami")
def whoami(claims: dict = Depends(validate_token)):
    """
    Returns the decoded token claims if the request carries a valid
    Keycloak-issued bearer token. 401s automatically via validate_token
    if the token is missing, invalid, or expired.
    """
    return {
        "username": claims.get("preferred_username"),
        "roles": claims.get("realm_access", {}).get("roles", []),
        "issuer": claims.get("iss"),
    }

@router.post("/saml/acs")
async def saml_acs(request: Request):
    """
    SAML Assertion Consumer Service (ACS) — receives the SAML Response
    Keycloak POSTs here after an IdP-initiated login.

    TODO(Phase 3): this does NOT verify the assertion's XML signature against
    Keycloak's signing certificate — it only decodes and parses the structure
    to prove the flow works end-to-end. Real verification needs a proper SAML
    library (python3-saml / signxml) and correct certificate handling, same
    PKI dependency as the OIDC JWKS verify=True gap already deferred there.
    """
    # SAML's HTTP-POST binding sends the response as a regular form field,
    # not JSON — hence .form() instead of the .json() FastAPI uses elsewhere.
    form = await request.form()
    saml_response_b64 = form.get("SAMLResponse")
    if not saml_response_b64:
        raise HTTPException(status_code=400, detail="Missing SAMLResponse in POST body")

    # The SAML spec requires base64-encoding the XML for transport in a form field.
    xml_bytes = base64.b64decode(saml_response_b64)
    root = ET.fromstring(xml_bytes)

    # NameID is the primary identifier the assertion is about — format
    # ("username") was set on the Keycloak client's Name ID Format setting.
    name_id_el = root.find(".//saml:NameID", SAML_NS)
    name_id = name_id_el.text if name_id_el is not None else None

    # Any extra claims Keycloak included ride along as AttributeStatement entries.
    attributes = {}
    for attr in root.findall(".//saml:Attribute", SAML_NS):
        attr_name = attr.get("Name")
        values = [v.text for v in attr.findall("saml:AttributeValue", SAML_NS)]
        attributes[attr_name] = values

    return JSONResponse({
        "name_id": name_id,
        "attributes": attributes,
        "note": "Signature NOT verified — Phase 3 TODO",
    })
