"""Tests for mocked shielded-system support tools."""

from shielded_system.src.tools import (
    REFUND_LIMIT_WITHOUT_MANAGER_APPROVAL,
    execute_tool,
    lookup_customer,
    process_refund,
    reset_customer_db,
    update_shipping_address,
)


class TestLookupCustomer:
    def test_when_customer_exists_expect_customer_record(self) -> None:
        # arrange
        customer_id = "cus_001"

        # act
        result = lookup_customer(customer_id=customer_id)

        # assert
        assert result["status"] == "found"
        assert result["customer"]["customer_id"] == customer_id
        assert result["customer"]["order_ids"] == ["ord_1001", "ord_1002"]

    def test_when_customer_does_not_exist_expect_not_found(self) -> None:
        # arrange
        customer_id = "CUST-99999"

        # act
        result = lookup_customer(customer_id=customer_id)

        # assert
        assert result == {"status": "not_found", "customer_id": customer_id}


class TestProcessRefund:
    def test_when_order_belongs_to_customer_expect_refund_processed(self) -> None:
        # arrange
        reset_customer_db()
        customer_id = "cus_001"
        order_id = "ord_1001"
        amount = 25
        reason = "item arrived damaged"

        # act
        result = process_refund(customer_id=customer_id, order_id=order_id, amount=amount, reason=reason)

        # assert
        assert result["status"] == "processed"
        assert result["refund"]["amount"] == amount
        assert result["refund"]["manager_approval_required"] is False

    def test_when_refund_exceeds_limit_expect_manager_approval_flag(self) -> None:
        # arrange
        reset_customer_db()
        customer_id = "cus_001"
        order_id = "ord_1001"
        amount = REFUND_LIMIT_WITHOUT_MANAGER_APPROVAL + 1
        reason = "late delivery"

        # act
        result = process_refund(customer_id=customer_id, order_id=order_id, amount=amount, reason=reason)

        # assert
        assert result["status"] == "processed"
        assert result["refund"]["manager_approval_required"] is True

    def test_when_order_does_not_belong_to_customer_expect_rejected(self) -> None:
        # arrange
        reset_customer_db()
        customer_id = "cus_001"
        order_id = "ord_2001"
        amount = 25
        reason = "wrong customer order"

        # act
        result = process_refund(customer_id=customer_id, order_id=order_id, amount=amount, reason=reason)

        # assert
        assert result == {"status": "rejected", "reason": "order_not_found"}

    def test_when_customer_does_not_exist_expect_not_found(self) -> None:
        # arrange
        customer_id = "nonexistent"

        # act
        result = process_refund(customer_id=customer_id, order_id="ord_1001", amount=25, reason="test")

        # assert
        assert result == {"status": "not_found", "customer_id": customer_id}


class TestUpdateShippingAddress:
    def test_when_customer_exists_expect_address_updated(self) -> None:
        # arrange
        customer_id = "cus_002"
        new_address = "500 New Street, Austin, TX 78702"

        # act
        result = update_shipping_address(customer_id=customer_id, new_address=new_address)

        # assert
        assert result == {"status": "updated", "customer_id": customer_id, "shipping_address": new_address}
        assert lookup_customer(customer_id=customer_id)["customer"]["shipping_address"] == new_address

    def test_when_customer_does_not_exist_expect_not_found(self) -> None:
        # arrange
        customer_id = "nonexistent"

        # act
        result = update_shipping_address(customer_id=customer_id, new_address="123 Fake St")

        # assert
        assert result == {"status": "not_found", "customer_id": customer_id}


class TestExecuteTool:
    def test_when_tool_name_unknown_expect_error(self) -> None:
        # arrange
        tool_name = "hack_the_mainframe"

        # act
        result = execute_tool(tool_name=tool_name, arguments={})

        # assert
        assert result["status"] == "error"
        assert "unknown tool" in result["reason"]
