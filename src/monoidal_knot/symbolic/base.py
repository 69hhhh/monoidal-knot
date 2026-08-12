"""Immutable exact scalars with commuting SymPy and Grassmann parts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from math import factorial
from typing import Any

import sympy  # type: ignore[import-untyped]
from sympy.core.expr import Expr  # type: ignore[import-untyped]

from monoidal_knot.errors import NonInvertibleError, ScalarDomainError, SymbolicError
from monoidal_knot.symbolic.grassmann import GrassmannAlgebra, GrassmannMonomial
from monoidal_knot.symbolic.parity import Parity

type ScalarInput = ScalarExpr | int | Fraction | Expr


@dataclass(frozen=True, slots=True, init=False, eq=False)
class ScalarExpr:
    """An exact sparse element of a finite Grassmann algebra.

    Each coefficient is an exact commuting SymPy expression.  A missing
    Grassmann algebra denotes an ordinary scalar and embeds into any registry.
    """

    _algebra: GrassmannAlgebra | None
    _terms: tuple[tuple[int, Expr], ...]

    def __init__(self, value: ScalarInput = 0) -> None:
        if isinstance(value, ScalarExpr):
            object.__setattr__(self, "_algebra", value.algebra)
            object.__setattr__(self, "_terms", value._terms)
            return
        coefficient = _normalize_coefficient(value)
        object.__setattr__(self, "_algebra", None)
        object.__setattr__(self, "_terms", () if coefficient == 0 else ((0, coefficient),))

    @classmethod
    def _from_generator(cls, algebra: GrassmannAlgebra, index: int) -> ScalarExpr:
        return cls._from_terms(algebra, {1 << index: sympy.Integer(1)})

    @classmethod
    def _from_terms(
        cls,
        algebra: GrassmannAlgebra | None,
        terms: Mapping[int, Expr],
    ) -> ScalarExpr:
        normalized: list[tuple[int, Expr]] = []
        for mask, coefficient in terms.items():
            if not isinstance(mask, int) or isinstance(mask, bool) or mask < 0:
                raise SymbolicError("A scalar term mask must be a nonnegative integer.")
            if mask and algebra is None:
                raise SymbolicError("A nonconstant Grassmann term requires an algebra registry.")
            if algebra is not None and mask.bit_length() > algebra.generator_count:
                raise SymbolicError("A scalar term references an unregistered Grassmann generator.")
            exact = _normalize_coefficient(coefficient)
            if exact != 0:
                normalized.append((mask, exact))
        normalized.sort(key=lambda item: item[0])
        result = object.__new__(cls)
        object.__setattr__(
            result, "_algebra", algebra if any(mask for mask, _ in normalized) else None
        )
        object.__setattr__(result, "_terms", tuple(normalized))
        return result

    @property
    def algebra(self) -> GrassmannAlgebra | None:
        """Return the Grassmann registry, or ``None`` for an ordinary scalar."""

        return self._algebra

    @property
    def terms(self) -> tuple[tuple[GrassmannMonomial | None, Expr], ...]:
        """Return normalized terms, using ``None`` for the constant monomial."""

        result: list[tuple[GrassmannMonomial | None, Expr]] = []
        for mask, coefficient in self._terms:
            monomial = None if mask == 0 else self._require_algebra().monomial(mask)
            result.append((monomial, coefficient))
        return tuple(result)

    @property
    def parity(self) -> Parity:
        """Classify all nonzero monomials as zero, even, odd, or mixed."""

        if not self._terms:
            return Parity.ZERO
        parities = {mask.bit_count() % 2 for mask, _ in self._terms}
        if parities == {0}:
            return Parity.EVEN
        if parities == {1}:
            return Parity.ODD
        return Parity.MIXED

    @property
    def is_zero(self) -> bool:
        """Whether exact normalization proved the expression to be zero."""

        return not self._terms

    @property
    def is_even(self) -> bool:
        """Whether every nonzero term has even degree; zero counts as even."""

        return self.parity in (Parity.ZERO, Parity.EVEN)

    @property
    def body(self) -> ScalarExpr:
        """Return the degree-zero commuting part."""

        for mask, coefficient in self._terms:
            if mask == 0:
                return ScalarExpr(coefficient)
        return ScalarExpr()

    def inverse(self) -> ScalarExpr:
        """Return the finite Grassmann-series inverse when the body is nonzero."""

        body = self.body
        if body.is_zero:
            raise NonInvertibleError(
                "A Grassmann expression is invertible only when its degree-zero part is nonzero."
            )
        body_inverse = ScalarExpr(1 / body.to_sympy())
        nilpotent = self - body
        if nilpotent.is_zero:
            return body_inverse
        unit_nilpotent = nilpotent * body_inverse
        result = ScalarExpr(1)
        term = ScalarExpr(1)
        algebra = nilpotent._require_algebra()
        for _ in range(1, algebra.generator_count + 1):
            term = -(term * unit_nilpotent)
            if term.is_zero:
                break
            result += term
        return body_inverse * result

    def exp(self) -> ScalarExpr:
        """Return the exact exponential with a finite nilpotent expansion."""

        body = self.body
        nilpotent = self - body
        body_exp = ScalarExpr(sympy.exp(body.to_sympy()))
        if nilpotent.is_zero:
            return body_exp
        result = ScalarExpr(1)
        power = ScalarExpr(1)
        algebra = nilpotent._require_algebra()
        for exponent in range(1, algebra.generator_count + 1):
            power *= nilpotent
            if power.is_zero:
                break
            result += power / factorial(exponent)
        return body_exp * result

    def to_sympy(self) -> Expr:
        """Return an ordinary SymPy expression, rejecting Grassmann terms."""

        if self.algebra is not None:
            raise SymbolicError("A scalar with Grassmann terms cannot be converted to SymPy.")
        if not self._terms:
            return sympy.Integer(0)
        return self._terms[0][1]

    def _require_algebra(self) -> GrassmannAlgebra:
        if self.algebra is None:
            raise SymbolicError("This scalar has no Grassmann algebra registry.")
        return self.algebra

    def _binary_algebra(self, other: ScalarExpr) -> GrassmannAlgebra | None:
        if (
            self.algebra is not None
            and other.algebra is not None
            and self.algebra is not other.algebra
        ):
            raise ScalarDomainError(
                f"Cannot combine Grassmann algebras {self.algebra.id!r} and {other.algebra.id!r}."
            )
        return self.algebra or other.algebra

    def __add__(self, other: ScalarInput) -> ScalarExpr:
        right = coerce_scalar(other)
        algebra = self._binary_algebra(right)
        terms = dict(self._terms)
        for mask, coefficient in right._terms:
            terms[mask] = terms.get(mask, sympy.Integer(0)) + coefficient
        return self._from_terms(algebra, terms)

    def __radd__(self, other: ScalarInput) -> ScalarExpr:
        return self + other

    def __neg__(self) -> ScalarExpr:
        return self._from_terms(self.algebra, {mask: -value for mask, value in self._terms})

    def __sub__(self, other: ScalarInput) -> ScalarExpr:
        return self + (-coerce_scalar(other))

    def __rsub__(self, other: ScalarInput) -> ScalarExpr:
        return coerce_scalar(other) - self

    def __mul__(self, other: ScalarInput) -> ScalarExpr:
        right = coerce_scalar(other)
        algebra = self._binary_algebra(right)
        if self.is_zero or right.is_zero:
            return ScalarExpr()
        products: dict[int, Expr] = {}
        for left_mask, left_coefficient in self._terms:
            for right_mask, right_coefficient in right._terms:
                if left_mask & right_mask:
                    continue
                swaps = 0
                remaining = left_mask
                while remaining:
                    lowest = remaining & -remaining
                    index = lowest.bit_length() - 1
                    swaps += (right_mask & ((1 << index) - 1)).bit_count()
                    remaining ^= lowest
                sign = -1 if swaps % 2 else 1
                mask = left_mask | right_mask
                value = sign * left_coefficient * right_coefficient
                products[mask] = products.get(mask, sympy.Integer(0)) + value
        return self._from_terms(algebra, products)

    def __rmul__(self, other: ScalarInput) -> ScalarExpr:
        return coerce_scalar(other) * self

    def __truediv__(self, other: ScalarInput) -> ScalarExpr:
        return self * coerce_scalar(other).inverse()

    def __rtruediv__(self, other: ScalarInput) -> ScalarExpr:
        return coerce_scalar(other) * self.inverse()

    def __pow__(self, exponent: int) -> ScalarExpr:
        if not isinstance(exponent, int) or isinstance(exponent, bool):
            raise SymbolicError("Scalar powers currently require an integer exponent.")
        if exponent < 0:
            return self.inverse() ** (-exponent)
        result = ScalarExpr(1)
        factor = self
        remaining = exponent
        while remaining:
            if remaining & 1:
                result *= factor
            factor *= factor
            remaining >>= 1
        return result

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ScalarExpr):
            return self.algebra is other.algebra and self._terms == other._terms
        try:
            coerced = coerce_scalar(other)
        except (SymbolicError, TypeError, ValueError):
            return False
        return self == coerced

    def __hash__(self) -> int:
        if not self._terms:
            return hash(0)
        if self.algebra is None:
            return hash(self._terms[0][1])
        return hash((id(self.algebra), self._terms))

    def __str__(self) -> str:
        if not self._terms:
            return "0"
        rendered: list[str] = []
        for mask, coefficient in self._terms:
            if mask == 0:
                rendered.append(str(coefficient))
                continue
            monomial = str(self._require_algebra().monomial(mask))
            if coefficient == 1:
                rendered.append(monomial)
            elif coefficient == -1:
                rendered.append(f"-{monomial}")
            else:
                rendered.append(f"({coefficient})*{monomial}")
        return " + ".join(rendered).replace("+ -", "- ")

    def __repr__(self) -> str:
        return f"ScalarExpr({str(self)!r})"


def Symbol(name: str, **assumptions: Any) -> ScalarExpr:
    """Construct one exact commuting symbol wrapped as a ``ScalarExpr``."""

    if not isinstance(name, str) or not name or name.isspace():
        raise SymbolicError("A commuting symbol name must be non-empty.")
    if assumptions.get("commutative") is False:
        raise SymbolicError("Ordinary coefficient symbols must be commuting.")
    assumptions["commutative"] = True
    return ScalarExpr(sympy.Symbol(name, **assumptions))


def coerce_scalar(value: object) -> ScalarExpr:
    """Coerce one supported exact scalar input into the unified wrapper."""

    if isinstance(value, ScalarExpr):
        return value
    if isinstance(value, (int, Fraction, Expr)) and not isinstance(value, bool):
        return ScalarExpr(value)
    raise TypeError(f"Unsupported exact scalar input: {type(value).__name__}.")


def _normalize_coefficient(value: object) -> Expr:
    if isinstance(value, bool) or isinstance(value, (float, complex)):
        raise SymbolicError("Inexact Python numeric values are not valid exact scalars.")
    if not isinstance(value, (int, Fraction, Expr)):
        raise TypeError(f"Unsupported exact coefficient: {type(value).__name__}.")
    expression = sympy.sympify(value)
    if not isinstance(expression, Expr):
        raise SymbolicError("A scalar coefficient must be a SymPy expression.")
    if expression.atoms(sympy.Float):
        raise SymbolicError("Floating-point coefficients are not valid exact scalars.")
    if expression.has(sympy.zoo, sympy.oo, -sympy.oo, sympy.nan):
        raise SymbolicError("Undefined or infinite coefficients are not valid exact scalars.")
    if expression.is_commutative is not True:
        raise SymbolicError("Scalar coefficients must commute with Grassmann generators.")
    normalized = sympy.cancel(expression)
    if not isinstance(normalized, Expr):
        raise SymbolicError("SymPy did not return a scalar expression during normalization.")
    return normalized
