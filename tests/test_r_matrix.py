from dataclasses import FrozenInstanceError
from fractions import Fraction

import pytest

from monoidal_knot import (
    BraidMorphism,
    CategorySpec,
    DefinitionError,
    ExactMatrix,
    ExactMatrixError,
    GrassmannAlgebra,
    RMatrixConvention,
    RMatrixFunctor,
    RMatrixSpec,
    Symbol,
)


def swap_2d() -> ExactMatrix:
    return ExactMatrix(
        [
            [1, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1],
        ]
    )


def test_object_dimensions_include_unit_tensor_words_and_duals() -> None:
    category = CategorySpec("dimensions")
    value = category.object("V")
    other = category.object("W")
    model = RMatrixFunctor(source=category, object_map={value: 2, other: 3})

    assert model.dimension(category.unit) == 1
    assert model.dimension(value.dual) == 2
    assert model.dimension(value.tensor(other).tensor(value.dual)) == 12
    with pytest.raises(DefinitionError, match="single non-dual"):
        RMatrixFunctor(source=category, object_map={value.dual: 2})
    with pytest.raises(DefinitionError, match="positive integer"):
        RMatrixFunctor(source=category, object_map={value: 0})


def test_r_spec_is_explicit_even_and_immutable() -> None:
    check_r = swap_2d()
    spec = RMatrixSpec(check_r, convention="check")

    assert spec.convention is RMatrixConvention.CHECK
    with pytest.raises(FrozenInstanceError):
        spec.matrix = ExactMatrix.identity(4)  # type: ignore[misc]
    with pytest.raises(DefinitionError, match=r"check.*quantum"):
        RMatrixSpec(check_r, convention="unknown")

    algebra = GrassmannAlgebra("odd-r")
    theta = algebra.symbol("theta")
    with pytest.raises(ExactMatrixError, match="even entries"):
        RMatrixSpec(ExactMatrix([[1, theta], [0, 1]]))


def test_quantum_r_is_converted_to_check_r_with_declared_basis_order() -> None:
    category = CategorySpec("quantum-to-check")
    left = category.object("A")
    right = category.object("B")
    model = RMatrixFunctor(
        source=category,
        object_map={left: 2, right: 3},
        r_matrices={(left, right): RMatrixSpec(ExactMatrix.identity(6), convention="quantum")},
    )

    converted = model.check_r(left, right)

    # source basis index a*3+b maps to target basis index b*2+a
    for a in range(2):
        for b in range(3):
            assert converted[b * 2 + a, a * 3 + b] == 1
    assert sum(not entry.is_zero for row in converted.rows for entry in row) == 6


def test_colored_negative_crossing_uses_reversed_pair_inverse() -> None:
    category = CategorySpec("colored-negative-r")
    red = category.object("red")
    blue = category.object("blue")
    model = RMatrixFunctor(
        source=category,
        object_map={red: 1, blue: 1},
        r_matrices={
            (red, blue): RMatrixSpec(ExactMatrix([[2]])),
            (blue, red): RMatrixSpec(ExactMatrix([[3]])),
        },
    )

    positive = BraidMorphism(red.tensor(blue), (1,))
    negative = BraidMorphism(red.tensor(blue), (-1,))

    assert model.evaluate_braid(positive) == ExactMatrix([[2]])
    assert model.evaluate_braid(negative) == ExactMatrix([[Fraction(1, 3)]])


def test_same_braid_can_be_evaluated_with_two_exact_r_data_sets() -> None:
    category = CategorySpec("replaceable-r")
    value = category.object("V")
    braid = BraidMorphism(value.tensor_power(2), (1,))
    q = Symbol("q")
    first = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        r_matrices={(value, value): RMatrixSpec(swap_2d())},
    )
    second = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        r_matrices={(value, value): RMatrixSpec(swap_2d() * q)},
    )

    assert first.evaluate_braid(braid) == swap_2d()
    assert second.evaluate_braid(braid) == swap_2d() * q
    assert first.evaluate_braid(braid) != second.evaluate_braid(braid)


def test_r_matrix_shape_is_checked_at_functor_construction() -> None:
    category = CategorySpec("r-shape")
    value = category.object("V")

    with pytest.raises(DefinitionError, match=r"shape \(4, 4\)"):
        RMatrixFunctor(
            source=category,
            object_map={value: 2},
            r_matrices={(value, value): RMatrixSpec(ExactMatrix.identity(2))},
        )
