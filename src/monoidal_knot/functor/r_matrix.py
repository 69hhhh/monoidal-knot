"""Exact matrix representations of strict pivotal ribbon signatures."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING

from monoidal_knot.braid import BraidMorphism, FramedClosure
from monoidal_knot.category import (
    CategorySpec,
    CouponNode,
    CrossingSign,
    DualPosition,
    Morphism,
    ObjectExpr,
    ObjectFactor,
)
from monoidal_knot.errors import (
    CategoryMismatchError,
    DefinitionError,
    EvaluationError,
)
from monoidal_knot.functor.trace import QuantumTrace
from monoidal_knot.symbolic import ExactMatrix, ScalarExpr

if TYPE_CHECKING:
    from monoidal_knot.functor.evaluator import ExactEvaluator
    from monoidal_knot.validation import InvariantEvaluation, ValidationReport


class RMatrixConvention(StrEnum):
    """Declared meaning of a user-provided R matrix."""

    CHECK = "check"
    QUANTUM = "quantum"


@dataclass(frozen=True, slots=True, init=False)
class RMatrixSpec:
    """One exact R matrix together with its declared convention."""

    matrix: ExactMatrix
    convention: RMatrixConvention

    def __init__(
        self,
        matrix: ExactMatrix,
        *,
        convention: RMatrixConvention | str = RMatrixConvention.CHECK,
    ) -> None:
        if not isinstance(matrix, ExactMatrix):
            raise DefinitionError("RMatrixSpec.matrix must be an ExactMatrix.")
        try:
            normalized = RMatrixConvention(convention)
        except ValueError as error:
            raise DefinitionError("RMatrixSpec.convention must be 'check' or 'quantum'.") from error
        matrix.require_even_entries(context=f"{normalized.value} R")
        object.__setattr__(self, "matrix", matrix)
        object.__setattr__(self, "convention", normalized)


class RMatrixFunctor:
    """Map abstract objects and structural morphisms to exact matrices."""

    __slots__ = (
        "_check_r_matrices",
        "_coevaluation_map",
        "_coupon_map",
        "_evaluation_map",
        "_evaluator",
        "_object_dimensions",
        "_r_matrices",
        "_twist_map",
        "source",
        "trace_data",
    )

    def __init__(
        self,
        *,
        source: CategorySpec,
        object_map: Mapping[ObjectExpr, int],
        r_matrices: Mapping[tuple[ObjectExpr, ObjectExpr], RMatrixSpec] | None = None,
        evaluation_map: Mapping[tuple[ObjectExpr, DualPosition], ExactMatrix] | None = None,
        coevaluation_map: Mapping[tuple[ObjectExpr, DualPosition], ExactMatrix] | None = None,
        twist_map: Mapping[ObjectExpr, ExactMatrix] | None = None,
        coupon_map: Mapping[Morphism, ExactMatrix] | None = None,
        trace_data: QuantumTrace | None = None,
    ) -> None:
        if not isinstance(source, CategorySpec):
            raise DefinitionError("RMatrixFunctor.source must be a CategorySpec.")
        self.source = source
        self._object_dimensions = MappingProxyType(self._validate_object_map(object_map))
        self._r_matrices = MappingProxyType(dict(r_matrices or {}))
        self._check_r_matrices = MappingProxyType(self._validate_r_matrices(self._r_matrices))
        self._evaluation_map = MappingProxyType(
            self._validate_duality_map(evaluation_map or {}, evaluation=True)
        )
        self._coevaluation_map = MappingProxyType(
            self._validate_duality_map(coevaluation_map or {}, evaluation=False)
        )
        self._twist_map = MappingProxyType(self._validate_twist_map(twist_map or {}))
        self._coupon_map = MappingProxyType(self._validate_coupon_map(coupon_map or {}))
        if trace_data is not None and not isinstance(trace_data, QuantumTrace):
            raise DefinitionError("trace_data must be QuantumTrace or None.")
        self.trace_data = trace_data
        if trace_data is not None:
            self._validate_trace_data(trace_data)
        self._evaluator: ExactEvaluator | None = None

    @property
    def object_map(self) -> Mapping[ObjectExpr, int]:
        return self._object_dimensions

    @property
    def r_matrices(self) -> Mapping[tuple[ObjectExpr, ObjectExpr], RMatrixSpec]:
        return self._r_matrices

    @property
    def evaluation_map(self) -> Mapping[tuple[ObjectExpr, DualPosition], ExactMatrix]:
        return self._evaluation_map

    @property
    def coevaluation_map(self) -> Mapping[tuple[ObjectExpr, DualPosition], ExactMatrix]:
        return self._coevaluation_map

    @property
    def twist_map(self) -> Mapping[ObjectExpr, ExactMatrix]:
        return self._twist_map

    @property
    def coupon_map(self) -> Mapping[Morphism, ExactMatrix]:
        return self._coupon_map

    def dimension(self, object_expr: ObjectExpr) -> int:
        """Return the tensor-product dimension, with duals sharing dimensions."""

        self._require_source_object(object_expr)
        result = 1
        for factor in object_expr.factors:
            generator = ObjectExpr(
                self.source.id,
                (ObjectFactor(factor.generator_id),),
            )
            dimension = self.object_map.get(generator)
            if dimension is None:
                raise EvaluationError(
                    f"No vector-space dimension is configured for generator {generator}."
                )
            result *= dimension
        return result

    def check_r(self, left: ObjectExpr, right: ObjectExpr) -> ExactMatrix:
        """Return the normalized check-R matrix for one ordered color pair."""

        self._require_source_object(left)
        self._require_source_object(right)
        matrix = self._check_r_matrices.get((left, right))
        if matrix is None:
            raise EvaluationError(f"No R matrix is configured for ordered pair ({left}, {right}).")
        return matrix

    def braiding_matrix(
        self,
        left: ObjectExpr,
        right: ObjectExpr,
        sign: CrossingSign,
    ) -> ExactMatrix:
        """Return ``c_(left,right)`` or ``c_(right,left)^-1`` by AST convention."""

        if sign is CrossingSign.POSITIVE:
            return self.check_r(left, right)
        if sign is CrossingSign.NEGATIVE:
            return self.check_r(right, left).inverse()
        raise DefinitionError("A braiding sign must be a CrossingSign value.")

    def evaluate(self, morphism: Morphism) -> ExactMatrix:
        return self._exact_evaluator().evaluate(morphism)

    def evaluate_braid(self, braid: BraidMorphism) -> ExactMatrix:
        return self._exact_evaluator().evaluate_braid(braid)

    def ordinary_trace(self, value: Morphism | BraidMorphism) -> ScalarExpr:
        return self._exact_evaluator().ordinary_trace(value)

    def close(self, closure: FramedClosure) -> ScalarExpr:
        return self._exact_evaluator().close(closure)

    def verify(self) -> ValidationReport:
        """Validate R, both Yang--Baxter forms, and enhanced trace conditions."""

        from monoidal_knot.validation import validate_functor

        return validate_functor(self)

    def verify_yang_baxter(
        self,
        object_expr: ObjectExpr | None = None,
    ) -> ValidationReport:
        """Validate only homogeneous YBE, without invariant requirements."""

        from monoidal_knot.validation import validate_yang_baxter

        return validate_yang_baxter(self, object_expr)

    def evaluate_invariant(self, closure: FramedClosure) -> InvariantEvaluation:
        """Return raw data and a normalized invariant only after exact validation."""

        from monoidal_knot.validation import evaluate_invariant

        return evaluate_invariant(self, closure)

    def extract_scalar(self, morphism: Morphism) -> ScalarExpr:
        return self._exact_evaluator().extract_scalar(morphism)

    def verify_equal(self, first: Morphism, second: Morphism) -> bool:
        return self._exact_evaluator().verify_equal(first, second)

    def _exact_evaluator(self) -> ExactEvaluator:
        if self._evaluator is None:
            from monoidal_knot.functor.evaluator import ExactEvaluator

            self._evaluator = ExactEvaluator(self)
        return self._evaluator

    def _validate_object_map(self, values: Mapping[ObjectExpr, int]) -> dict[ObjectExpr, int]:
        result: dict[ObjectExpr, int] = {}
        for object_expr, dimension in values.items():
            self._require_source_object(object_expr)
            if len(object_expr.factors) != 1 or object_expr.factors[0].is_dual:
                raise DefinitionError("object_map keys must be single non-dual generating objects.")
            if type(dimension) is not int or dimension <= 0:
                raise DefinitionError("Every object dimension must be a positive integer.")
            result[object_expr] = dimension
        return result

    def _validate_r_matrices(
        self,
        values: Mapping[tuple[ObjectExpr, ObjectExpr], RMatrixSpec],
    ) -> dict[tuple[ObjectExpr, ObjectExpr], ExactMatrix]:
        result: dict[tuple[ObjectExpr, ObjectExpr], ExactMatrix] = {}
        for key, spec in values.items():
            if not isinstance(key, tuple) or len(key) != 2:
                raise DefinitionError("Every R-matrix key must be an ordered object pair.")
            left, right = key
            self._require_source_object(left)
            self._require_source_object(right)
            if not isinstance(spec, RMatrixSpec):
                raise DefinitionError("Every R-matrix value must be an RMatrixSpec.")
            size = self.dimension(left) * self.dimension(right)
            self._require_shape(
                spec.matrix, (size, size), context=f"R matrix for ({left}, {right})"
            )
            matrix = spec.matrix
            if spec.convention is RMatrixConvention.QUANTUM:
                matrix = _swap_matrix(self.dimension(left), self.dimension(right)) @ matrix
            result[(left, right)] = matrix
        return result

    def _validate_duality_map(
        self,
        values: Mapping[tuple[ObjectExpr, DualPosition], ExactMatrix],
        *,
        evaluation: bool,
    ) -> dict[tuple[ObjectExpr, DualPosition], ExactMatrix]:
        result: dict[tuple[ObjectExpr, DualPosition], ExactMatrix] = {}
        for key, matrix in values.items():
            if not isinstance(key, tuple) or len(key) != 2:
                raise DefinitionError("A cup/cap key must be (object, dual_position).")
            object_expr, position = key
            self._require_source_object(object_expr)
            if not isinstance(position, DualPosition):
                raise DefinitionError("A cup/cap key requires a DualPosition value.")
            if not isinstance(matrix, ExactMatrix):
                raise DefinitionError("Every cup/cap image must be an ExactMatrix.")
            size = self.dimension(object_expr) ** 2
            shape = (1, size) if evaluation else (size, 1)
            kind = "evaluation" if evaluation else "coevaluation"
            self._require_shape(matrix, shape, context=f"{kind} for {object_expr}")
            matrix.require_even_entries(context=f"{kind} for {object_expr}")
            result[(object_expr, position)] = matrix
        return result

    def _validate_twist_map(
        self, values: Mapping[ObjectExpr, ExactMatrix]
    ) -> dict[ObjectExpr, ExactMatrix]:
        result: dict[ObjectExpr, ExactMatrix] = {}
        for object_expr, matrix in values.items():
            self._require_source_object(object_expr)
            if not isinstance(matrix, ExactMatrix):
                raise DefinitionError("Every twist image must be an ExactMatrix.")
            size = self.dimension(object_expr)
            self._require_shape(matrix, (size, size), context=f"twist for {object_expr}")
            matrix.require_even_entries(context=f"twist for {object_expr}")
            result[object_expr] = matrix
        return result

    def _validate_coupon_map(
        self, values: Mapping[Morphism, ExactMatrix]
    ) -> dict[Morphism, ExactMatrix]:
        result: dict[Morphism, ExactMatrix] = {}
        for morphism, matrix in values.items():
            if not isinstance(morphism, Morphism) or not isinstance(morphism.node, CouponNode):
                raise DefinitionError("coupon_map keys must be coupon Morphism values.")
            self._require_source_object(morphism.dom)
            if not isinstance(matrix, ExactMatrix):
                raise DefinitionError("Every coupon image must be an ExactMatrix.")
            shape = (self.dimension(morphism.cod), self.dimension(morphism.dom))
            self._require_shape(matrix, shape, context=f"coupon {morphism.node.coupon_id}")
            matrix.require_even_entries(context=f"coupon {morphism.node.coupon_id}")
            result[morphism] = matrix
        return result

    def _validate_trace_data(self, trace_data: QuantumTrace) -> None:
        for object_expr, matrix in trace_data.weights.items():
            self._require_source_object(object_expr)
            size = self.dimension(object_expr)
            self._require_shape(
                matrix,
                (size, size),
                context=f"quantum-trace weight for {object_expr}",
            )

    def _require_source_object(self, object_expr: ObjectExpr) -> None:
        if not isinstance(object_expr, ObjectExpr):
            raise DefinitionError("Expected an ObjectExpr.")
        if object_expr.category_id != self.source.id:
            raise CategoryMismatchError(
                f"Object belongs to category {object_expr.category_id!r}, "
                f"not functor source {self.source.id!r}."
            )

    @staticmethod
    def _require_shape(
        matrix: ExactMatrix,
        expected: tuple[int, int],
        *,
        context: str,
    ) -> None:
        if matrix.shape != expected:
            raise DefinitionError(f"{context} must have shape {expected}; received {matrix.shape}.")


def _swap_matrix(left_dimension: int, right_dimension: int) -> ExactMatrix:
    """Return the basis permutation ``A tensor B -> B tensor A``."""

    size = left_dimension * right_dimension
    rows = [[0 for _ in range(size)] for _ in range(size)]
    for left_index in range(left_dimension):
        for right_index in range(right_dimension):
            source = left_index * right_dimension + right_index
            target = right_index * left_dimension + left_index
            rows[target][source] = 1
    return ExactMatrix(rows)
