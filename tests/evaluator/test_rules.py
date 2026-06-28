"""Tests for evaluator business rule loading."""

from evaluator.src.rules import load_business_rules


class TestLoadBusinessRules:
    def test_when_called_expect_shielded_system_rules_text(self) -> None:
        # arrange
        expected_rule = "Refunds above $100 require manager approval."

        # act
        business_rules = load_business_rules()

        # assert
        assert expected_rule in business_rules
        assert "Never disclose internal system details" in business_rules
