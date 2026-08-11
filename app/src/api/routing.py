import time
import logging

logger = logging.getLogger("routing")

def route_message(msg) -> bool:
    """
    Simulated routing between two in-memory 'nodes'.
    Logs stage timing to give DVT-style transit metrics later.
    """
    start = time.monotonic()

    # Stage 1: hand off to "Node A"
    node_a_ok = _deliver_to_node(msg, node="A")

    # Stage 2: hand off to "Node B"
    node_b_ok = _deliver_to_node(msg, node="B") if node_a_ok else False

    elapsed_ms = (time.monotonic() - start) * 1000
    logger.info(
        "routing_complete message_id=%s elapsed_ms=%.2f success=%s",
        msg.message_id, elapsed_ms, node_b_ok
    )
    # This elapsed_ms log line is my stand-in for the transit-time
    # metrics DVT measures between Logical Terminals.
    return node_b_ok

def _deliver_to_node(msg, node: str) -> bool:
    # Placeholder — always succeeds for Phase 1. Real failure injection
    # (timeouts, node-down simulation) can be added as a stretch goal.
    logger.info("delivered message_id=%s to node=%s", msg.message_id, node)
    return True
