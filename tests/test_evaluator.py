from fractions import Fraction

import pytest

from monoidal_knot import (
    BraidMorphism,
    CategorySpec,
    DualPosition,
    EvaluationError,
    ExactMatrix,
    MorphismTypeError,
    ObjectExpr,
    QuantumTrace,
    RMatrixFunctor,
    RMatrixSpec,
    Symbol,
    verify_equal,
)

SWAP = ExactMatrix(
    [
        [1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
    ]
)


def braid_model(category: CategorySpec, value: ObjectExpr) -> RMatrixFunctor:
    return RMatrixFunctor(
        source=category,
        object_map={value: 2},
        r_matrices={(value, value): RMatrixSpec(SWAP)},
    )


def test_recursive_ast_and_direct_braid_evaluation_agree() -> None:
    category = CategorySpec("two-evaluation-paths")
    value = category.object("V")
    model = braid_model(category, value)
    braid = BraidMorphism(value.tensor_power(3), (1, -2, 1))

    assert model.evaluate(braid.expand()) == model.evaluate_braid(braid)


def test_basic_braid_relation_is_exactly_equal_in_a_valid_representation() -> None:
    category = CategorySpec("braid-relation-evaluation")
    value = category.object("V")
    model = braid_model(category, value)
    objects = value.tensor_power(3)
    left = BraidMorphism(objects, (1, 2, 1))
    right = BraidMorphism(objects, (2, 1, 2))

    assert model.evaluate_braid(left) == model.evaluate_braid(right)
    assert model.verify_equal(left.expand(), right.expand())
    assert verify_equal(left.expand(), right.expand(), functor=model)


def test_coupon_composition_tensor_cups_caps_twist_and_scalar_extraction() -> None:
    category = CategorySpec("all-ast-nodes")
    value = category.object("V")
    coupon = category.coupon("f", value, value)
    cap = category.evaluation(value, dual_position=DualPosition.LEFT)
    cup = category.coevaluation(value, dual_position=DualPosition.LEFT)
    twist = category.twist(value)
    inverse_twist = category.twist(value, inverse=True)
    coupon_matrix = ExactMatrix([[1, 2], [0, 1]])
    cap_matrix = ExactMatrix([[1, 0, 0, 1]])
    cup_matrix = ExactMatrix([[1], [0], [0], [1]])
    twist_matrix = ExactMatrix([[2, 0], [0, 3]])
    model = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        evaluation_map={(value, DualPosition.LEFT): cap_matrix},
        coevaluation_map={(value, DualPosition.LEFT): cup_matrix},
        twist_map={value: twist_matrix},
        coupon_map={coupon: coupon_matrix},
    )

    assert model.evaluate(coupon.then(coupon)) == coupon_matrix @ coupon_matrix
    assert model.evaluate(coupon.tensor(coupon)) == coupon_matrix.tensor(coupon_matrix)
    assert model.evaluate(cap) == cap_matrix
    assert model.evaluate(cup) == cup_matrix
    assert model.evaluate(twist) == twist_matrix
    assert model.evaluate(inverse_twist) == ExactMatrix([[Fraction(1, 2), 0], [0, Fraction(1, 3)]])
    assert model.extract_scalar(cup.then(cap)) == 2


def test_missing_coupon_or_structural_data_fails_explicitly() -> None:
    category = CategorySpec("missing-images")
    value = category.object("V")
    model = RMatrixFunctor(source=category, object_map={value: 2})

    with pytest.raises(EvaluationError, match=r"No matrix.*coupon"):
        model.evaluate(category.coupon("f", value, value))
    with pytest.raises(EvaluationError, match="No evaluation matrix"):
        model.evaluate(category.evaluation(value, dual_position=DualPosition.RIGHT))
    with pytest.raises(EvaluationError, match="No twist matrix"):
        model.evaluate(category.twist(value))


def test_ordinary_and_quantum_trace_are_distinct_and_closure_is_explicit() -> None:
    category = CategorySpec("trace")
    value = category.object("V")
    q = Symbol("q")
    braid = BraidMorphism.identity(value)
    without_trace = RMatrixFunctor(source=category, object_map={value: 2})
    with_trace = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        trace_data=QuantumTrace(weights={value: ExactMatrix([[q, 0], [0, 1]])}),
    )

    assert with_trace.ordinary_trace(braid) == 2
    assert with_trace.close(braid.close()) == q + 1
    with pytest.raises(EvaluationError, match="never used implicitly"):
        without_trace.close(braid.close())


def test_quantum_trace_is_tensor_multiplicative() -> None:
    category = CategorySpec("tensor-trace")
    value = category.object("V")
    q = Symbol("q")
    braid = BraidMorphism.identity(value.tensor_power(2))
    model = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        trace_data=QuantumTrace(weights={value: ExactMatrix([[q, 0], [0, 1]])}),
    )

    assert model.close(braid.close()) == (q + 1) ** 2


def test_trace_and_representation_equality_require_matching_types() -> None:
    category = CategorySpec("trace-types")
    value = category.object("V")
    model = RMatrixFunctor(source=category, object_map={value: 2})
    non_endomorphism = category.coupon("state", category.unit, value)

    with pytest.raises(MorphismTypeError, match="endomorphism"):
        model.ordinary_trace(non_endomorphism)
    with pytest.raises(MorphismTypeError, match="matching morphism types"):
        model.verify_equal(category.identity(value), category.identity(value.tensor_power(2)))
    with pytest.raises(MorphismTypeError, match="I -> I"):
        model.extract_scalar(category.identity(value))
