from enum import StrEnum


class AccountType(StrEnum):
    CASH = "cash"
    BANK = "bank"
    SAVINGS = "savings"
    CARD = "card"
    OTHER = "other"
