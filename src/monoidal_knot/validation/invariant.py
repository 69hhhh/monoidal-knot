"""Exact validation of R-matrix and enhanced Markov-trace data."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from monoidal_knot.category import ObjectExpr
from monoidal_knot.errors import EvaluationError, NonInvertibleError
from monoidal_knot.symbolic import ExactMatrix, ScalarExpr
from monoidal_knot.validation.report import CheckStatus, ValidationCheck, ValidationReport
from monoidal_knot.validation.yang_baxter import (
    braid_yang_baxter_residual,
    check_to_quantum,
    quantum_yang_baxter_residual,
)

if TYPE_CHECKING:
    from monoidal_knot.braid import FramedClosure
    from monoidal_knot.functor import RMatrixFunctor


class EvaluationClassification(StrEnum):
    """Whether a closure value is only raw or passed all invariant checks."""

    RAW_EVALUATION = "raw_evaluation"
    VERIFIED_INVARIANT = "verified_invariant"


@dataclass(frozen=True, slots=True)
class InvariantEvaluation:
    """A raw closure value plus a normalized value only when verification passed."""

    closure: FramedClosure
    raw_value: ScalarExpr
    normalized_value: ScalarExpr | None
    report: ValidationReport

    @property
    def verified(self) -> bool:
        return self.report.verified and self.normalized_value is not None

    @property
    def classification(self) -> EvaluationClassification:
        if self.verified:
            return EvaluationClassification.VERIFIED_INVARIANT
        return EvaluationClassification.RAW_EVALUATION


def validate_functor(functor: RMatrixFunctor) -> ValidationReport:
    """Validate exact homogeneous R and enhanced trace data without overclaiming.

    Stage 5 certifies the one-object/homogeneous route used by the Jones example.
    Colored heterogeneous Yang--Baxter systems remain evaluable, but are not
    promoted to verified invariants by this validator.
    """

    checks: list[ValidationCheck] = []
    configured = tuple(functor.r_matrices.items())
    generators = tuple(functor.object_map)
    checks.append(
        _pass("r.configured", f"{len(configured)} R-matrix specification(s) configured")
        if configured
        else _fail("r.configured", "No R matrix is configured")
    )

    stage5_object = generators[0] if len(generators) == 1 else None
    checks.append(
        _pass(
            "r.stage5-scope",
            "The functor has one generating object, within the stage-5 certificate scope",
        )
        if stage5_object is not None
        else _fail(
            "r.stage5-scope",
            "The stage-5 invariant certificate supports exactly one generating object",
            evidence=tuple(str(generator) for generator in generators),
        )
    )

    homogeneous: list[tuple[ObjectExpr, ExactMatrix, int, str]] = []
    for index, ((left, right), spec) in enumerate(configured):
        label = f"({left}, {right})"
        size = functor.dimension(left) * functor.dimension(right)
        expected = (size, size)
        checks.append(
            _pass(f"r.{index}.shape", f"R matrix {label} has shape {expected}")
            if spec.matrix.shape == expected
            else _fail(
                f"r.{index}.shape",
                f"R matrix {label} has shape {spec.matrix.shape}, expected {expected}",
                evidence=spec.matrix.shape,
            )
        )
        checks.append(
            _pass(f"r.{index}.parity", f"R matrix {label} has only even entries")
            if spec.matrix.is_even
            else _fail(
                f"r.{index}.parity",
                f"R matrix {label} contains odd or mixed entries",
                evidence=spec.matrix.non_even_entries(),
            )
        )
        check_r = functor.check_r(left, right)
        try:
            inverse = check_r.inverse()
        except NonInvertibleError as error:
            checks.append(
                _fail(
                    f"r.{index}.invertible",
                    f"R matrix {label} is not invertible",
                    evidence=str(error),
                )
            )
        else:
            identity = ExactMatrix.identity(size)
            residual = check_r @ inverse - identity
            checks.append(
                _pass(f"r.{index}.invertible", f"R matrix {label} has an exact inverse")
                if _is_zero_matrix(residual)
                else _fail(
                    f"r.{index}.invertible",
                    f"R matrix {label} failed its inverse residual check",
                    evidence=residual,
                )
            )
        if left == right and len(left.factors) == 1:
            homogeneous.append((left, check_r, functor.dimension(left), label))

    checks.append(
        _pass(
            "r.homogeneous-coverage",
            f"{len(homogeneous)} homogeneous generating-object R matrix/matrices can be certified",
        )
        if homogeneous
        else _skip(
            "r.homogeneous-coverage",
            "No homogeneous generating-object R matrix is available for stage-5 certification",
        )
    )

    for index, (_, check_r, dimension, label) in enumerate(homogeneous):
        braid_residual = braid_yang_baxter_residual(check_r, dimension=dimension)
        checks.append(
            _residual_check(
                f"ybe.{index}.braid",
                braid_residual,
                passed_summary=f"R matrix {label} satisfies the braid-form Yang--Baxter equation",
                failed_summary=f"R matrix {label} fails the braid-form Yang--Baxter equation",
            )
        )
        quantum_r = check_to_quantum(check_r, dimension=dimension)
        quantum_residual = quantum_yang_baxter_residual(quantum_r, dimension=dimension)
        checks.append(
            _residual_check(
                f"ybe.{index}.quantum",
                quantum_residual,
                passed_summary=f"R matrix {label} satisfies the quantum-form Yang--Baxter equation",
                failed_summary=f"R matrix {label} fails the quantum-form Yang--Baxter equation",
            )
        )

    trace_data = functor.trace_data
    if trace_data is None:
        checks.append(_skip("trace.configured", "No categorical trace data is configured"))
        return ValidationReport.from_checks(checks)
    checks.append(_pass("trace.configured", "Categorical trace data is configured"))

    for index, (object_expr, configured_weight) in enumerate(trace_data.weights.items()):
        if len(object_expr.factors) <= 1:
            continue
        factorized = ExactMatrix.identity(1)
        try:
            for factor in object_expr.factors:
                factorized = factorized.tensor(
                    trace_data.matrix_for(ObjectExpr(object_expr.category_id, (factor,)))
                )
        except EvaluationError as error:
            checks.append(
                _fail(
                    f"trace.composite.{index}",
                    f"Composite trace weight for {object_expr} lacks factor data",
                    evidence=str(error),
                )
            )
        else:
            checks.append(
                _residual_check(
                    f"trace.composite.{index}",
                    configured_weight - factorized,
                    passed_summary=f"Trace weight for {object_expr} is tensor-multiplicative",
                    failed_summary=(f"Trace weight for {object_expr} is not tensor-multiplicative"),
                )
            )

    parameters = trace_data.parameters
    if parameters is None:
        checks.append(
            _skip(
                "trace.markov-parameters",
                "No alpha, beta, and overall normalization are configured",
            )
        )
        return ValidationReport.from_checks(checks)
    checks.append(
        _pass("trace.markov-parameters", "Explicit Markov trace parameters are configured")
    )

    for index, (object_expr, check_r, _, label) in enumerate(homogeneous):
        try:
            mu = trace_data.matrix_for(object_expr)
        except EvaluationError as error:
            checks.append(
                _fail(
                    f"trace.{index}.weight",
                    f"No usable trace weight exists for {object_expr}",
                    evidence=str(error),
                )
            )
            continue
        checks.append(_pass(f"trace.{index}.weight", f"Trace weight for {object_expr} is present"))
        try:
            mu_inverse = mu.inverse()
        except NonInvertibleError as error:
            checks.append(
                _fail(
                    f"trace.{index}.weight-invertible",
                    f"Trace weight for {object_expr} is not invertible",
                    evidence=str(error),
                )
            )
        else:
            weight_identity = ExactMatrix.identity(mu.shape[0])
            checks.append(
                _residual_check(
                    f"trace.{index}.weight-invertible",
                    mu @ mu_inverse - weight_identity,
                    passed_summary=f"Trace weight for {object_expr} has an exact inverse",
                    failed_summary=f"Trace weight for {object_expr} failed its inverse residual check",
                )
            )

        tensor_weight = mu.tensor(mu)
        checks.append(
            _residual_check(
                f"trace.{index}.commutes",
                check_r @ tensor_weight - tensor_weight @ check_r,
                passed_summary=f"Trace weight commutes with R matrix {label}",
                failed_summary=f"Trace weight does not commute with R matrix {label}",
            )
        )
        positive = _partial_trace_second(check_r @ tensor_weight, dimension=mu.shape[0])
        checks.append(
            _residual_check(
                f"trace.{index}.positive-stabilization",
                positive - mu * (parameters.alpha * parameters.beta),
                passed_summary="Positive Markov stabilization identity holds exactly",
                failed_summary="Positive Markov stabilization identity has a nonzero residual",
            )
        )
        try:
            inverse_r = check_r.inverse()
        except NonInvertibleError as error:
            checks.append(
                _fail(
                    f"trace.{index}.negative-stabilization",
                    "Negative Markov stabilization cannot hold because R is not invertible",
                    evidence=str(error),
                )
            )
        else:
            negative = _partial_trace_second(inverse_r @ tensor_weight, dimension=mu.shape[0])
            checks.append(
                _residual_check(
                    f"trace.{index}.negative-stabilization",
                    negative - mu * (parameters.alpha**-1 * parameters.beta),
                    passed_summary="Negative Markov stabilization identity holds exactly",
                    failed_summary=(
                        "Negative Markov stabilization identity has a nonzero residual"
                    ),
                )
            )

    return ValidationReport.from_checks(checks)


def validate_yang_baxter(
    functor: RMatrixFunctor,
    object_expr: ObjectExpr | None = None,
) -> ValidationReport:
    """Check only the homogeneous Yang--Baxter equations for one object.

    This deliberately does not require invertibility, trace data, Markov
    parameters, or normalization.  A passing report certifies only the two
    equivalent YBE forms for the selected exact matrix; it is not an invariant
    certificate.

    When ``object_expr`` is omitted, the functor must have exactly one
    generating object and it is selected automatically.
    """

    generators = tuple(functor.object_map)
    if object_expr is None:
        if len(generators) != 1:
            return ValidationReport.from_checks(
                (
                    _fail(
                        "ybe.object",
                        "Select an object explicitly when the functor does not have exactly one generator",
                        evidence=tuple(str(generator) for generator in generators),
                    ),
                )
            )
        object_expr = generators[0]
    elif object_expr not in functor.object_map:
        return ValidationReport.from_checks(
            (
                _fail(
                    "ybe.object",
                    "The selected object must be a configured non-dual generator",
                    evidence=str(object_expr),
                ),
            )
        )

    checks = [
        _pass(
            "ybe.object",
            f"Selected homogeneous generating object {object_expr}",
        )
    ]
    try:
        check_r = functor.check_r(object_expr, object_expr)
    except EvaluationError as error:
        checks.append(
            _fail(
                "ybe.r-configured",
                f"No homogeneous R matrix is configured for {object_expr}",
                evidence=str(error),
            )
        )
        return ValidationReport.from_checks(checks)

    checks.append(
        _pass(
            "ybe.r-configured",
            f"Homogeneous R matrix for {object_expr} is configured",
        )
    )
    dimension = functor.dimension(object_expr)
    braid_residual = braid_yang_baxter_residual(check_r, dimension=dimension)
    checks.append(
        _residual_check(
            "ybe.braid",
            braid_residual,
            passed_summary="The braid-form Yang--Baxter equation holds exactly",
            failed_summary="The braid-form Yang--Baxter equation has a nonzero residual",
        )
    )
    quantum_r = check_to_quantum(check_r, dimension=dimension)
    quantum_residual = quantum_yang_baxter_residual(quantum_r, dimension=dimension)
    checks.append(
        _residual_check(
            "ybe.quantum",
            quantum_residual,
            passed_summary="The quantum-form Yang--Baxter equation holds exactly",
            failed_summary="The quantum-form Yang--Baxter equation has a nonzero residual",
        )
    )
    return ValidationReport.from_checks(checks)


def evaluate_invariant(functor: RMatrixFunctor, closure: FramedClosure) -> InvariantEvaluation:
    """Return raw closure data and only expose a normalized value after validation."""

    raw_value = functor.close(closure)
    report = validate_functor(functor)
    generators = tuple(functor.object_map)
    closure_supported = len(generators) == 1 and all(
        factor == generators[0].factors[0] for factor in closure.braid.dom.factors
    )
    closure_check = (
        _pass(
            "closure.stage5-scope",
            "Every closure strand uses the certified generating object",
        )
        if closure_supported
        else _fail(
            "closure.stage5-scope",
            "The closure contains strands outside the homogeneous stage-5 certificate scope",
            evidence=str(closure.braid.dom),
        )
    )
    report = ValidationReport.from_checks((*report.checks, closure_check))
    parameters = functor.trace_data.parameters if functor.trace_data is not None else None
    normalized = None
    if report.verified and parameters is not None:
        normalized = parameters.normalize(
            raw_value,
            strands=closure.braid.strands,
            writhe=closure.writhe,
        )
    return InvariantEvaluation(closure, raw_value, normalized, report)


def _partial_trace_second(matrix: ExactMatrix, *, dimension: int) -> ExactMatrix:
    expected = dimension**2
    if matrix.shape != (expected, expected):
        raise EvaluationError(
            f"A two-factor partial trace expected shape {(expected, expected)}, "
            f"received {matrix.shape}."
        )
    return ExactMatrix(
        [
            [
                sum(
                    (
                        matrix[row * dimension + inner, column * dimension + inner]
                        for inner in range(dimension)
                    ),
                    ScalarExpr(),
                )
                for column in range(dimension)
            ]
            for row in range(dimension)
        ]
    )


def _is_zero_matrix(matrix: ExactMatrix) -> bool:
    return all(entry.is_zero for row in matrix.rows for entry in row)


def _residual_check(
    key: str,
    residual: ExactMatrix,
    *,
    passed_summary: str,
    failed_summary: str,
) -> ValidationCheck:
    if _is_zero_matrix(residual):
        return _pass(key, passed_summary, evidence=residual)
    return _fail(key, failed_summary, evidence=residual)


def _pass(key: str, summary: str, *, evidence: object | None = None) -> ValidationCheck:
    return ValidationCheck(key, CheckStatus.PASSED, summary, evidence=evidence)


def _fail(key: str, summary: str, *, evidence: object | None = None) -> ValidationCheck:
    return ValidationCheck(key, CheckStatus.FAILED, summary, evidence=evidence)


def _skip(key: str, summary: str) -> ValidationCheck:
    return ValidationCheck(key, CheckStatus.SKIPPED, summary)
