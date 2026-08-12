"""Recursive and direct exact evaluators for morphisms and braid words."""

from __future__ import annotations

from typing import TYPE_CHECKING

from monoidal_knot.braid import BraidMorphism, FramedClosure
from monoidal_knot.category import (
    BraidingNode,
    CoevaluationNode,
    ComposeNode,
    CouponNode,
    EvaluationNode,
    IdentityNode,
    Morphism,
    ObjectExpr,
    TensorNode,
    TwistNode,
)
from monoidal_knot.errors import (
    CategoryMismatchError,
    EvaluationError,
    MorphismTypeError,
)
from monoidal_knot.symbolic import ExactMatrix, ScalarExpr

if TYPE_CHECKING:
    from monoidal_knot.functor.r_matrix import RMatrixFunctor


class ExactEvaluator:
    """Interpret immutable syntax using one fixed R-matrix functor."""

    __slots__ = ("_cache", "functor")

    def __init__(self, functor: RMatrixFunctor) -> None:
        self.functor = functor
        self._cache: dict[Morphism, ExactMatrix] = {}

    def evaluate(self, morphism: Morphism) -> ExactMatrix:
        """Recursively evaluate one typed morphism with exact arithmetic."""

        if not isinstance(morphism, Morphism):
            raise EvaluationError("ExactEvaluator.evaluate requires a Morphism.")
        self._require_category(morphism.category_id)
        cached = self._cache.get(morphism)
        if cached is not None:
            return cached

        node = morphism.node
        if isinstance(node, IdentityNode):
            result = ExactMatrix.identity(self.functor.dimension(morphism.dom))
        elif isinstance(node, ComposeNode):
            result = self.evaluate(node.morphisms[0])
            for child in node.morphisms[1:]:
                result = self.evaluate(child) @ result
        elif isinstance(node, TensorNode):
            result = self.evaluate(node.morphisms[0])
            for child in node.morphisms[1:]:
                result = result.tensor(self.evaluate(child))
        elif isinstance(node, BraidingNode):
            result = self.functor.braiding_matrix(node.left, node.right, node.sign)
        elif isinstance(node, EvaluationNode):
            configured_evaluation = self.functor.evaluation_map.get(
                (node.object, node.dual_position)
            )
            if configured_evaluation is None:
                raise EvaluationError(
                    f"No evaluation matrix is configured for ({node.object}, "
                    f"{node.dual_position.value})."
                )
            result = configured_evaluation
        elif isinstance(node, CoevaluationNode):
            configured_coevaluation = self.functor.coevaluation_map.get(
                (node.object, node.dual_position)
            )
            if configured_coevaluation is None:
                raise EvaluationError(
                    f"No coevaluation matrix is configured for ({node.object}, "
                    f"{node.dual_position.value})."
                )
            result = configured_coevaluation
        elif isinstance(node, TwistNode):
            configured_twist = self.functor.twist_map.get(node.object)
            if configured_twist is None:
                raise EvaluationError(f"No twist matrix is configured for {node.object}.")
            result = configured_twist.inverse() if node.inverse else configured_twist
        elif isinstance(node, CouponNode):
            configured_coupon = self.functor.coupon_map.get(morphism)
            if configured_coupon is None:
                raise EvaluationError(
                    f"No matrix is configured for coupon {node.coupon_id!r} with type {morphism}."
                )
            result = configured_coupon
        else:
            raise EvaluationError(f"Unsupported morphism node {type(node).__name__}.")

        expected = (self.functor.dimension(morphism.cod), self.functor.dimension(morphism.dom))
        if result.shape != expected:
            raise EvaluationError(
                f"Evaluation of {type(node).__name__} produced shape {result.shape}; "
                f"expected {expected}."
            )
        self._cache[morphism] = result
        return result

    def evaluate_braid(self, braid: BraidMorphism) -> ExactMatrix:
        """Evaluate a compact braid word by embedding local R matrices."""

        if not isinstance(braid, BraidMorphism):
            raise EvaluationError("evaluate_braid requires a BraidMorphism.")
        self._require_category(braid.category_id)
        current = braid.dom
        result = ExactMatrix.identity(self.functor.dimension(current))

        for generator in braid.word:
            index = abs(generator) - 1
            left = ObjectExpr(braid.category_id, (current.factors[index],))
            right = ObjectExpr(braid.category_id, (current.factors[index + 1],))
            from monoidal_knot.category import CrossingSign

            sign = CrossingSign.POSITIVE if generator > 0 else CrossingSign.NEGATIVE
            crossing = self.functor.braiding_matrix(left, right, sign)
            prefix = ObjectExpr(braid.category_id, current.factors[:index])
            suffix = ObjectExpr(braid.category_id, current.factors[index + 2 :])
            local = (
                ExactMatrix.identity(self.functor.dimension(prefix))
                .tensor(crossing)
                .tensor(ExactMatrix.identity(self.functor.dimension(suffix)))
            )
            result = local @ result
            factors = list(current.factors)
            factors[index], factors[index + 1] = factors[index + 1], factors[index]
            current = ObjectExpr(braid.category_id, tuple(factors))

        return result

    def ordinary_trace(self, value: Morphism | BraidMorphism) -> ScalarExpr:
        """Return an explicitly requested ordinary matrix trace."""

        if isinstance(value, Morphism):
            if value.dom != value.cod:
                raise MorphismTypeError("Ordinary trace requires an endomorphism.")
            return self.evaluate(value).trace()
        if isinstance(value, BraidMorphism):
            if value.dom != value.cod:
                raise MorphismTypeError("Ordinary trace requires an endomorphism braid.")
            return self.evaluate_braid(value).trace()
        raise EvaluationError("ordinary_trace requires a Morphism or BraidMorphism.")

    def close(self, closure: FramedClosure) -> ScalarExpr:
        """Evaluate a blackboard-framed closure using explicit quantum-trace data."""

        if not isinstance(closure, FramedClosure):
            raise EvaluationError("close requires a FramedClosure.")
        self._require_category(closure.category_id)
        trace_data = self.functor.trace_data
        if trace_data is None:
            raise EvaluationError(
                "Categorical closure requires explicit QuantumTrace data; "
                "ordinary trace is never used implicitly."
            )
        matrix = self.evaluate_braid(closure.braid)
        weight = trace_data.matrix_for(closure.braid.dom)
        if weight.shape != matrix.shape:
            raise EvaluationError(
                f"Quantum-trace weight has shape {weight.shape}; expected {matrix.shape}."
            )
        return (weight @ matrix).trace()

    def extract_scalar(self, morphism: Morphism) -> ScalarExpr:
        """Extract the unique entry of an evaluated ``I -> I`` morphism."""

        if not morphism.dom.is_unit or not morphism.cod.is_unit:
            raise MorphismTypeError("Scalar extraction requires a morphism of type I -> I.")
        matrix = self.evaluate(morphism)
        if matrix.shape != (1, 1):
            raise EvaluationError(f"An I -> I image must have shape (1, 1), not {matrix.shape}.")
        return matrix[0, 0]

    def verify_equal(self, first: Morphism, second: Morphism) -> bool:
        """Check exact equality in this representation, not diagrammatic equality."""

        if first.dom != second.dom or first.cod != second.cod:
            raise MorphismTypeError("Representation equality requires matching morphism types.")
        return self.evaluate(first) == self.evaluate(second)

    def _require_category(self, category_id: str) -> None:
        if category_id != self.functor.source.id:
            raise CategoryMismatchError(
                f"Expression belongs to category {category_id!r}, "
                f"not functor source {self.functor.source.id!r}."
            )


def verify_equal(first: Morphism, second: Morphism, *, functor: RMatrixFunctor) -> bool:
    """Convenience wrapper for exact equality in a specified representation."""

    return functor.verify_equal(first, second)
