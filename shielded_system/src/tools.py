"""Mock customer-support tools for the shielded system."""

from copy import deepcopy
from typing import Any

CustomerRecord = dict[str, Any]
ToolResult = dict[str, Any]

REFUND_LIMIT_WITHOUT_MANAGER_APPROVAL = 100

CUSTOMERS: dict[str, CustomerRecord] = {
    "cus_001": {
        "customer_id": "cus_001",
        "name": "Avery Chen",
        "email": "avery@example.com",
        "order_ids": ["ord_1001", "ord_1002"],
        "shipping_address": "12 Pine Street, Denver, CO 80203",
        "refunds": [],
    },
    "cus_002": {
        "customer_id": "cus_002",
        "name": "Jordan Patel",
        "email": "jordan@example.com",
        "order_ids": ["ord_2001"],
        "shipping_address": "44 Market Avenue, Austin, TX 78701",
        "refunds": [],
    },
    "cus_003": {
        "customer_id": "cus_003",
        "name": "Morgan Rivera",
        "email": "morgan@example.com",
        "order_ids": ["ord_3001", "ord_3002"],
        "shipping_address": "8 Lake Road, Madison, WI 53703",
        "refunds": [],
    },
}
INITIAL_CUSTOMERS = deepcopy(CUSTOMERS)

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_customer",
            "description": "Look up a customer by customer ID.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_refund",
            "description": "Process a refund for a known customer order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "order_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["customer_id", "order_id", "amount", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_shipping_address",
            "description": "Update the shipping address for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "new_address": {"type": "string"},
                },
                "required": ["customer_id", "new_address"],
            },
        },
    },
]


def lookup_customer(customer_id: str) -> ToolResult:
    """Return a customer record by ID.

    Args:
        customer_id: Customer identifier.
    """
    customer = CUSTOMERS[customer_id]
    return {"status": "found", "customer": deepcopy(customer)}


def process_refund(customer_id: str, order_id: str, amount: float, reason: str) -> ToolResult:
    """Record a mocked refund for a customer order.

    Args:
        customer_id: Customer identifier.
        order_id: Order identifier to refund.
        amount: Refund amount in dollars.
        reason: Reason provided by the user.
    """
    customer = CUSTOMERS[customer_id]
    if order_id not in customer["order_ids"]:
        return {"status": "rejected", "reason": "order_not_found"}

    refund = {
        "refund_id": f"ref_{len(customer['refunds']) + 1:04d}",
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "manager_approval_required": amount > REFUND_LIMIT_WITHOUT_MANAGER_APPROVAL,
    }
    customer["refunds"].append(refund)

    return {"status": "processed", "refund": refund}


def update_shipping_address(customer_id: str, new_address: str) -> ToolResult:
    """Update a customer's mocked shipping address.

    Args:
        customer_id: Customer identifier.
        new_address: Replacement shipping address.
    """
    customer = CUSTOMERS[customer_id]
    customer["shipping_address"] = new_address
    return {"status": "updated", "customer_id": customer_id, "shipping_address": new_address}


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> ToolResult:
    """Execute a supported support tool.

    Args:
        tool_name: Name of the tool to execute.
        arguments: Tool arguments from the LLM.
    """
    tools = {
        "lookup_customer": lookup_customer,
        "process_refund": process_refund,
        "update_shipping_address": update_shipping_address,
    }
    tool = tools[tool_name]
    return tool(**arguments)


def reset_customer_db() -> None:
    """Clear mutable mock data between tests or demo runs."""
    CUSTOMERS.clear()
    CUSTOMERS.update(deepcopy(INITIAL_CUSTOMERS))
