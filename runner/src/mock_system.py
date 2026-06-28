"""Mock shielded system for developing the attack runner independently."""

from runner.src.models import ShieldedSystemResponse, ToolExecution

MOCK_CUSTOMER_ID = "CUST-001"
MOCK_ORDER_ID = "ORD-1001"
MOCK_REFUND_AMOUNT = 90


class MockShieldedSystem:
    """Deterministic shielded system test double for Stream C."""

    async def chat(
        self, message: str, history: list[tuple[str, str]], security_tip: str | None = None
    ) -> ShieldedSystemResponse:
        """Respond to a user message and optionally simulate a tool call.

        Args:
            message: User message to process.
            history: Prior conversation turns as role/content tuples.
            security_tip: Optional security advisory (ignored by mock).
        """
        refund_count = _count_prior_refunds(history) + 1
        refund_id = f"REF-{refund_count:03d}"
        tool_execution = ToolExecution(
            tool_name="process_refund",
            arguments={
                "customer_id": MOCK_CUSTOMER_ID,
                "order_id": MOCK_ORDER_ID,
                "amount": MOCK_REFUND_AMOUNT,
            },
            result={
                "status": "success",
                "refund_id": refund_id,
                "amount": MOCK_REFUND_AMOUNT,
            },
        )
        response = f"I processed refund {refund_id} for ${MOCK_REFUND_AMOUNT} on order {MOCK_ORDER_ID}."
        return ShieldedSystemResponse(content=response, tool_executions=[tool_execution])


def _count_prior_refunds(history: list[tuple[str, str]]) -> int:
    refund_marker = "I processed refund"
    return sum(1 for role, content in history if role == "assistant" and refund_marker in content)
