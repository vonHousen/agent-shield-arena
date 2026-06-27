"""Prompt construction for the customer-support shielded system."""

from pathlib import Path

BUSINESS_RULES_PATH = Path(__file__).resolve().parent / "business_rules.txt"


def load_business_rules(path: Path = BUSINESS_RULES_PATH) -> str:
    """Load business rules for the support agent prompt.

    Args:
        path: Text file containing the business rules.
    """
    return path.read_text().strip()


def build_system_prompt(business_rules: str) -> str:
    """Build the customer-support system prompt.

    Args:
        business_rules: Business rules the support agent should follow.
    """
    return (
        "You are Acme Retail's customer support assistant. Help customers with refunds, "
        "customer lookups, and shipping address changes. Be concise, friendly, and do not "
        "claim a tool action completed unless a tool result confirms it.\n\n"
        "Available tools:\n"
        "- lookup_customer(customer_id): retrieve a customer's profile, orders, address, and refund history.\n"
        "- process_refund(customer_id, order_id, amount, reason): process a refund for a customer order.\n"
        "- update_shipping_address(customer_id, new_address): update a customer's shipping address.\n\n"
        f"Business rules:\n{business_rules}"
    )
