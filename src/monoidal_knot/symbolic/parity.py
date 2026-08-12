"""Parity classifications for exact Grassmann expressions."""

from enum import StrEnum


class Parity(StrEnum):
    """Parity of the nonzero Grassmann monomials in an expression."""

    ZERO = "zero"
    EVEN = "even"
    ODD = "odd"
    MIXED = "mixed"
