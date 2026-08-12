from dataclasses import FrozenInstanceError
from fractions import Fraction

import pytest
import sympy

from monoidal_knot import (
    GrassmannAlgebra,
    NonInvertibleError,
    Parity,
    ScalarDomainError,
    ScalarExpr,
    Symbol,
    SymbolicError,
)


def test_commuting_symbols_and_exact_coefficients_use_one_wrapper() -> None:
    q = Symbol("q")

    expression = q + Fraction(1, 3) + q

    assert isinstance(expression, ScalarExpr)
    assert expression == 2 * q + sympy.Rational(1, 3)
    assert expression.parity is Parity.EVEN
    assert ScalarExpr(2) == 2
    assert hash(ScalarExpr(2)) == hash(2)
    with pytest.raises(FrozenInstanceError):
        expression._terms = ()  # type: ignore[misc]


def test_inexact_and_noncommuting_coefficients_are_rejected() -> None:
    noncommuting = sympy.Symbol("x", commutative=False)

    with pytest.raises(SymbolicError, match="Inexact"):
        ScalarExpr(0.5)  # type: ignore[arg-type]
    with pytest.raises(SymbolicError, match="Floating-point"):
        ScalarExpr(sympy.Float("0.5"))
    with pytest.raises(SymbolicError, match="infinite"):
        ScalarExpr(sympy.zoo)
    with pytest.raises(SymbolicError, match="commute"):
        ScalarExpr(noncommuting)


def test_registry_is_append_only_and_generators_are_reused_by_name() -> None:
    algebra = GrassmannAlgebra("exterior")
    theta_1, theta_2 = algebra.symbols("theta_1", "theta_2")

    assert algebra.generator_names == ("theta_1", "theta_2")
    assert algebra.symbol("theta_1") == theta_1
    assert theta_1 != theta_2
    assert theta_1.algebra is algebra


def test_bitset_monomials_compute_anticommutation_signs() -> None:
    algebra = GrassmannAlgebra("monomials")
    algebra.symbols("a", "b", "c")
    a = algebra.monomial(0b001)
    b = algebra.monomial(0b010)
    ab = algebra.monomial(0b011)

    assert a.degree == 1
    assert ab.degree == 2
    assert ab.names == ("a", "b")
    assert a.multiply(b) == (1, ab)
    assert b.multiply(a) == (-1, ab)
    assert a.multiply(a) == (0, None)


def test_grassmann_products_are_anticommuting_nilpotent_and_canonical() -> None:
    algebra = GrassmannAlgebra("relations")
    theta_1, theta_2 = algebra.symbols("theta_1", "theta_2")

    assert theta_1 * theta_2 == -(theta_2 * theta_1)
    assert theta_1**2 == 0
    assert (theta_1 + theta_2) ** 2 == 0
    assert 2 * theta_1 * theta_2 + 3 * theta_2 * theta_1 == -(theta_1 * theta_2)


def test_parity_distinguishes_zero_even_odd_and_mixed_expressions() -> None:
    algebra = GrassmannAlgebra("parity")
    theta_1, theta_2, theta_3 = algebra.symbols("theta_1", "theta_2", "theta_3")
    q = Symbol("q")

    assert ScalarExpr().parity is Parity.ZERO
    assert (q + theta_1 * theta_2).parity is Parity.EVEN
    assert (theta_1 + theta_1 * theta_2 * theta_3).parity is Parity.ODD
    assert (q + theta_1).parity is Parity.MIXED
    assert ScalarExpr().is_even
    assert not (q + theta_1).is_even


def test_incompatible_registries_do_not_merge_even_when_ids_match() -> None:
    first = GrassmannAlgebra("same-id")
    second = GrassmannAlgebra("same-id")
    theta = first.symbol("theta")
    eta = second.symbol("eta")

    with pytest.raises(ScalarDomainError, match="Cannot combine"):
        _ = theta + eta
    with pytest.raises(ScalarDomainError, match="Cannot combine"):
        _ = theta * eta


def test_safe_inverse_uses_a_finite_nilpotent_series() -> None:
    algebra = GrassmannAlgebra("inverse")
    theta_1, theta_2 = algebra.symbols("theta_1", "theta_2")
    q = Symbol("q")
    value = q + theta_1 * theta_2

    expected = 1 / q - theta_1 * theta_2 / q**2

    assert value.inverse() == expected
    assert value * value.inverse() == 1
    assert (1 + theta_1).inverse() == 1 - theta_1
    assert (1 + theta_1 * theta_2) ** -1 == 1 - theta_1 * theta_2
    with pytest.raises(NonInvertibleError, match="degree-zero"):
        theta_1.inverse()
    with pytest.raises(NonInvertibleError, match="degree-zero"):
        (theta_1 * theta_2).inverse()


def test_exponential_splits_the_body_and_truncates_nilpotent_terms() -> None:
    algebra = GrassmannAlgebra("exponential")
    theta_1, theta_2, theta_3, theta_4 = algebra.symbols("theta_1", "theta_2", "theta_3", "theta_4")
    q = Symbol("q")

    assert theta_1.exp() == 1 + theta_1
    assert (theta_1 + theta_2).exp() == 1 + theta_1 + theta_2
    assert (q + theta_1 * theta_2).exp() == sympy.exp(q.to_sympy()) * (1 + theta_1 * theta_2)
    even_nilpotent = theta_1 * theta_2 + theta_3 * theta_4
    assert even_nilpotent.exp() == (
        1 + theta_1 * theta_2 + theta_3 * theta_4 + theta_1 * theta_2 * theta_3 * theta_4
    )


def test_only_ordinary_scalars_can_be_unwrapped_as_sympy_expressions() -> None:
    algebra = GrassmannAlgebra("conversion")
    theta = algebra.symbol("theta")
    q = Symbol("q")

    assert q.to_sympy() == sympy.Symbol("q")
    with pytest.raises(SymbolicError, match="cannot be converted"):
        theta.to_sympy()
