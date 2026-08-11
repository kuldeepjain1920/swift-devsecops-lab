import logging
import json

audit_logger = logging.getLogger("audit")

def log_transition(message_id: str, from_status: str, to_status: str, **extra):
    """
    Structured audit log for every status transition.
    JSON format so this can later be shipped to Cloud Logging / a SIEM
    without a reformatting step.
    """
    audit_logger.info(json.dumps({
        "event": "status_transition",
        "message_id": message_id,
        "from": from_status,
        "to": to_status,
        **extra,  # e.g. elapsed_ms from routing, for DVT-style SLA tracking
    }))
