package payment.authz

# Under threshold, initiator-only role — should be allowed.
test_small_amount_initiator_allowed if {
    allow with input as {
        "action": "submit",
        "roles": ["payment-initiator"],
        "amount": 5000,
    }
}

# Over threshold, initiator-only role — should be DENIED.
test_large_amount_initiator_only_denied if {
    not allow with input as {
        "action": "submit",
        "roles": ["payment-initiator"],
        "amount": 50000,
    }
}

# Over threshold, initiator AND approver roles both present — should be allowed.
test_large_amount_with_approver_allowed if {
    allow with input as {
        "action": "submit",
        "roles": ["payment-initiator", "payment-approver"],
        "amount": 50000,
    }
}
