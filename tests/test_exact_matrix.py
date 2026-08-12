from dataclasses import FrozenInstanceError

import pytest

from monoidal_knot import (
    ExactMatrix,
    ExactMatrixError,
    GrassmannAlgebra,
    Parity,
    ScalarDomainError,
    Symbol,
)


def test_matrix_construction_is_exact_immutable_and_shape_checked() -> None:
    q = Symbol("q")
    matrix = ExactMatrix([[1, q], [0, 2]])

    assert matrix.shape == (2, 2)
    assert matrix[0, 1] == q
    assert matrix.rows[1][1] == 2
    assert hash(matrix) == hash(ExactMatrix([[1, q], [0, 2]]))
    with pytest.raises(FrozenInstanceError):
        matrix._rows = ()  # type: ignore[misc]
    with pytest.raises(ExactMatrixError, match="at least one"):
        ExactMatrix([])
    with pytest.raises(ExactMatrixError, match="same length"):
        ExactMatrix([[1], [2, 3]])


def test_matrix_addition_multiplication_and_scaling_are_exact() -> None:
    q = Symbol("q")
    left = ExactMatrix([[q, 1], [0, q]])
    right = ExactMatrix([[1, 0], [1, 1]])

    assert left + right == ExactMatrix([[q + 1, 1], [1, q + 1]])
    assert left @ right == ExactMatrix([[q + 1, 1], [q, q]])
    assert 2 * left == ExactMatrix([[2 * q, 2], [0, 2 * q]])
    assert left * 2 == ExactMatrix([[2 * q, 2], [0, 2 * q]])
    assert left @ ExactMatrix.identity(2) == left
    with pytest.raises(ExactMatrixError, match="shapes"):
        _ = left @ ExactMatrix([[1]])


def test_ordinary_kronecker_product_preserves_entry_order() -> None:
    algebra = GrassmannAlgebra("tensor")
    theta_1, theta_2 = algebra.symbols("theta_1", "theta_2")
    left = ExactMatrix([[theta_1, 2]])
    right = ExactMatrix([[theta_2], [1]])

    assert left.tensor(right) == ExactMatrix([[theta_1 * theta_2, 2 * theta_2], [theta_1, 2]])


def test_matrix_parity_reports_every_non_even_entry() -> None:
    algebra = GrassmannAlgebra("matrix-parity")
    theta_1, theta_2 = algebra.symbols("theta_1", "theta_2")
    q = Symbol("q")
    even_matrix = ExactMatrix([[q, theta_1 * theta_2], [0, 1]])
    invalid_r_matrix = ExactMatrix([[q + theta_1, 0], [theta_2, 1]])

    assert even_matrix.parity is Parity.EVEN
    assert even_matrix.is_even
    assert invalid_r_matrix.parity is Parity.MIXED
    assert invalid_r_matrix.non_even_entries() == (
        (0, 0, Parity.MIXED),
        (1, 0, Parity.ODD),
    )
    with pytest.raises(
        ExactMatrixError,
        match=r"check_R requires even entries; found \(0, 0\)=mixed, \(1, 0\)=odd",
    ):
        invalid_r_matrix.require_even_entries(context="check_R")


def test_one_matrix_cannot_mix_independent_grassmann_registries() -> None:
    first = GrassmannAlgebra("first")
    second = GrassmannAlgebra("second")

    with pytest.raises(ScalarDomainError, match="cannot mix"):
        ExactMatrix([[first.symbol("theta"), second.symbol("eta")]])


def test_zero_and_identity_sizes_must_be_positive() -> None:
    assert ExactMatrix.zeros(2, 3).shape == (2, 3)
    assert ExactMatrix.identity(2) == ExactMatrix([[1, 0], [0, 1]])
    with pytest.raises(ExactMatrixError, match="positive"):
        ExactMatrix.zeros(0, 2)
