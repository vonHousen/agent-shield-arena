"""Business rule loading for evaluator prompts."""

from pathlib import Path

BUSINESS_RULES_PATH = Path("shielded_system/src/business_rules.txt")


def load_business_rules() -> str:
    """Load the shielded system business rules text."""
    return BUSINESS_RULES_PATH.read_text()
