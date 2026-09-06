package payment.authz

# Default deny — OPA policies should fail closed, not open.
# If no rule below explicitly matches, this is what applies.
default allow := false

# Rule 1: a payment-initiator can submit as long as the amount
# is at or under the threshold — this is the common case.
allow if {
    input.action == "submit"
    "payment-initiator" in input.roles
    input.amount <= 10000
}

# Rule 2: above the threshold, payment-initiator alone is not enough —
# the token must ALSO carry payment-approver. This is the actual ABAC
# behavior: the decision depends on an attribute of the REQUEST (amount),
# not just who the caller is.
allow if {
    input.action == "submit"
    "payment-initiator" in input.roles
    input.amount > 10000
    "payment-approver" in input.roles
}
