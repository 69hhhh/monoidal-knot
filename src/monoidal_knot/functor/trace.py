"""Explicit ordinary and categorical trace data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from monoidal_knot.category.objects import ObjectExpr
from monoidal_knot.errors import DefinitionError, EvaluationError, NonInvertibleError
from monoidal_knot.symbolic.base import ScalarExpr, ScalarInput, coerce_scalar
from monoidal_knot.symbolic.matrix import ExactMatrix


@dataclass(frozen=True, slots=True, init=False)
class MarkovTraceParameters:
    """Explicit normalization data for an enhanced Yang--Baxter operator.

    For an ``n``-strand braid ``b`` with writhe ``w``, the normalized value is

    ``overall_scale * alpha**(-w) * beta**(-n) * raw_quantum_trace``.

    ``overall_scale`` does not enter the Markov compatibility equations.  It
    is useful, for example, to choose the Jones convention ``V(unknot) = 1``.
    """

    alpha: ScalarExpr
    beta: ScalarExpr
    overall_scale: ScalarExpr

    def __init__(
        self,
        *,
        alpha: ScalarInput,
        beta: ScalarInput,
        overall_scale: ScalarInput = 1,
    ) -> None:
        converted = tuple(coerce_scalar(value) for value in (alpha, beta, overall_scale))
        for name, value in zip(("alpha", "beta", "overall_scale"), converted, strict=True):
            if not value.is_even:
                raise DefinitionError(f"Markov trace parameter {name} must be even.")
            try:
                value.inverse()
            except NonInvertibleError as error:
                raise DefinitionError(
                    f"Markov trace parameter {name} must be invertible."
                ) from error
            object.__setattr__(self, name, value)

    def normalize(self, raw_value: ScalarExpr, *, strands: int, writhe: int) -> ScalarExpr:
        """Apply the declared Markov and overall normalization exactly."""

        if type(strands) is not int or strands <= 0:
            raise DefinitionError("A normalized braid closure must have a positive strand count.")
        if type(writhe) is not int:
            raise DefinitionError("A braid writhe must be an integer.")
        return self.overall_scale * self.alpha ** (-writhe) * self.beta ** (-strands) * raw_value


class QuantumTrace:
    """Tensor-multiplicative weight matrices for ``Tr(mu_X @ f)``.

    The class stores data only.  Compatibility with braiding, pivotal, and
    ribbon structure is deliberately a stage-5 validation concern.
    """

    __slots__ = ("_weights", "parameters")

    def __init__(
        self,
        weights: Mapping[ObjectExpr, ExactMatrix],
        *,
        parameters: MarkovTraceParameters | None = None,
    ) -> None:
        copied = dict(weights)
        if not copied:
            raise DefinitionError("QuantumTrace requires at least one weight matrix.")
        for object_expr, matrix in copied.items():
            if not isinstance(object_expr, ObjectExpr):
                raise DefinitionError("Every quantum-trace key must be an ObjectExpr.")
            if object_expr.is_unit:
                raise DefinitionError(
                    "Do not configure a quantum-trace weight for the unit object."
                )
            if not isinstance(matrix, ExactMatrix):
                raise DefinitionError("Every quantum-trace weight must be an ExactMatrix.")
            matrix.require_even_entries(context=f"quantum-trace weight for {object_expr}")
        self._weights: Mapping[ObjectExpr, ExactMatrix] = MappingProxyType(copied)
        if parameters is not None and not isinstance(parameters, MarkovTraceParameters):
            raise DefinitionError("QuantumTrace.parameters must be MarkovTraceParameters or None.")
        self.parameters = parameters

    @property
    def weights(self) -> Mapping[ObjectExpr, ExactMatrix]:
        """Return the read-only explicit weight mapping."""

        return self._weights

    def matrix_for(self, object_expr: ObjectExpr) -> ExactMatrix:
        """Build the weight of a tensor word from explicit factor weights."""

        configured = self.weights.get(object_expr)
        if configured is not None:
            return configured
        if object_expr.is_unit:
            return ExactMatrix.identity(1)

        result = ExactMatrix.identity(1)
        for factor in object_expr.factors:
            factor_object = ObjectExpr(object_expr.category_id, (factor,))
            weight = self.weights.get(factor_object)
            if weight is None:
                raise EvaluationError(
                    f"No quantum-trace weight is configured for tensor factor {factor_object}."
                )
            result = result.tensor(weight)
        return result
