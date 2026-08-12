"""Canonical object expressions for strict monoidal categories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from monoidal_knot.errors import CategoryMismatchError, DefinitionError


def _require_identifier(value: str, *, kind: str) -> None:
    if not value or value.isspace():
        raise DefinitionError(f"A {kind} identifier must be non-empty.")


@dataclass(frozen=True, slots=True)
class ObjectFactor:
    """One generating object or its chosen pivotal dual."""

    generator_id: str
    is_dual: bool = False

    def __post_init__(self) -> None:
        _require_identifier(self.generator_id, kind="generating object")
        if not isinstance(self.is_dual, bool):
            raise DefinitionError("ObjectFactor.is_dual must be a boolean.")

    @property
    def dual(self) -> Self:
        """Return the chosen dual factor, using strict pivotal involutivity."""

        return type(self)(self.generator_id, not self.is_dual)


@dataclass(frozen=True, slots=True)
class ObjectExpr:
    """An immutable tensor word; the empty word is the unit object."""

    category_id: str
    factors: tuple[ObjectFactor, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.category_id, kind="category")
        if not isinstance(self.factors, tuple):
            raise DefinitionError("Object factors must be stored as a tuple.")
        if not all(isinstance(factor, ObjectFactor) for factor in self.factors):
            raise DefinitionError("Every object factor must be an ObjectFactor.")

    @property
    def is_unit(self) -> bool:
        """Whether this expression is the empty tensor word."""

        return not self.factors

    def tensor(self, other: ObjectExpr) -> ObjectExpr:
        """Form the strict tensor product by concatenating tensor words."""

        if self.category_id != other.category_id:
            raise CategoryMismatchError(
                "Cannot tensor objects from different categories: "
                f"{self.category_id!r} and {other.category_id!r}."
            )
        return type(self)(self.category_id, self.factors + other.factors)

    @property
    def dual(self) -> ObjectExpr:
        """Reverse the word and dualize its factors."""

        return type(self)(self.category_id, tuple(factor.dual for factor in reversed(self.factors)))

    def tensor_power(self, exponent: int) -> ObjectExpr:
        """Return a nonnegative strict tensor power."""

        if exponent < 0:
            raise DefinitionError("A tensor-power exponent must be nonnegative.")
        return type(self)(self.category_id, self.factors * exponent)

    def __str__(self) -> str:
        if self.is_unit:
            return "I"
        return " ⊗ ".join(
            f"{factor.generator_id}*" if factor.is_dual else factor.generator_id
            for factor in self.factors
        )
