from fractions import Fraction

from monoidal_knot import (
    BraidMorphism,
    CategorySpec,
    CheckStatus,
    EvaluationClassification,
    ExactMatrix,
    MarkovTraceParameters,
    QuantumTrace,
    RMatrixFunctor,
    RMatrixSpec,
)

SWAP = ExactMatrix(
    [
        [1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
    ]
)


def test_missing_markov_data_stays_a_raw_evaluation() -> None:
    category = CategorySpec("raw-not-invariant")
    value = category.object("V")
    model = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        r_matrices={(value, value): RMatrixSpec(SWAP)},
        trace_data=QuantumTrace({value: ExactMatrix.identity(2)}),
    )

    result = model.evaluate_invariant(BraidMorphism.identity(value).close())

    assert result.raw_value == 2
    assert result.normalized_value is None
    assert not result.verified
    assert result.classification is EvaluationClassification.RAW_EVALUATION
    assert result.report.status is CheckStatus.UNKNOWN
    assert result.report.inconclusive[0].key == "trace.markov-parameters"


def test_non_yang_baxter_matrix_reports_an_exact_nonzero_residual() -> None:
    category = CategorySpec("bad-ybe")
    value = category.object("V")
    bad_r = ExactMatrix(
        [
            [1, 0, 0, 0],
            [0, 2, 0, 0],
            [0, 0, 3, 0],
            [0, 0, 0, 4],
        ]
    )
    model = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        r_matrices={(value, value): RMatrixSpec(bad_r)},
    )

    report = model.verify()
    ybe_failure = next(check for check in report.failures if check.key == "ybe.0.braid")

    assert report.status is CheckStatus.FAILED
    assert isinstance(ybe_failure.evidence, ExactMatrix)
    assert any(not entry.is_zero for row in ybe_failure.evidence.rows for entry in row)


def test_singular_r_is_not_promoted_to_verified_data() -> None:
    category = CategorySpec("singular-r")
    value = category.object("V")
    singular = ExactMatrix(
        [
            [1, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
    )
    model = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        r_matrices={(value, value): RMatrixSpec(singular)},
        trace_data=QuantumTrace(
            {value: ExactMatrix.identity(2)},
            parameters=MarkovTraceParameters(alpha=1, beta=1),
        ),
    )

    report = model.verify()

    assert report.status is CheckStatus.FAILED
    assert next(check for check in report.failures if check.key == "r.0.invertible")
    assert next(check for check in report.failures if check.key == "trace.0.negative-stabilization")


def test_markov_normalization_formula_records_writhe_and_strand_correction() -> None:
    parameters = MarkovTraceParameters(alpha=2, beta=3, overall_scale=5)

    assert parameters.normalize(7, strands=2, writhe=-1) == Fraction(70, 9)


def test_composite_trace_override_must_be_tensor_multiplicative() -> None:
    category = CategorySpec("bad-composite-trace")
    value = category.object("V")
    model = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        r_matrices={(value, value): RMatrixSpec(SWAP)},
        trace_data=QuantumTrace(
            {
                value: ExactMatrix.identity(2),
                value.tensor_power(2): 2 * ExactMatrix.identity(4),
            },
            parameters=MarkovTraceParameters(alpha=1, beta=1),
        ),
    )

    report = model.verify()

    assert report.status is CheckStatus.FAILED
    assert next(check for check in report.failures if check.key.startswith("trace.composite."))


def test_ybe_only_validation_needs_no_trace_or_invertibility() -> None:
    category = CategorySpec("ybe-only-singular")
    value = category.object("V")
    model = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        r_matrices={(value, value): RMatrixSpec(ExactMatrix.zeros(4, 4))},
    )

    report = model.verify_yang_baxter()

    assert report.status is CheckStatus.PASSED
    assert report.verified
    assert tuple(check.key for check in report.checks) == (
        "ybe.object",
        "ybe.r-configured",
        "ybe.braid",
        "ybe.quantum",
    )
    assert model.verify().status is CheckStatus.FAILED


def test_ybe_only_validation_reports_nonzero_residual() -> None:
    category = CategorySpec("ybe-only-failure")
    value = category.object("V")
    bad_r = ExactMatrix(
        [
            [1, 0, 0, 0],
            [0, 2, 0, 0],
            [0, 0, 3, 0],
            [0, 0, 0, 4],
        ]
    )
    model = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        r_matrices={(value, value): RMatrixSpec(bad_r)},
    )

    report = model.verify_yang_baxter(value)

    assert report.status is CheckStatus.FAILED
    assert {check.key for check in report.failures} == {"ybe.braid", "ybe.quantum"}


def test_ybe_only_validation_can_select_one_object_in_multi_object_functor() -> None:
    category = CategorySpec("ybe-object-selection")
    value = category.object("V")
    other = category.object("W")
    model = RMatrixFunctor(
        source=category,
        object_map={value: 2, other: 1},
        r_matrices={(value, value): RMatrixSpec(SWAP)},
    )

    assert model.verify_yang_baxter().status is CheckStatus.FAILED
    assert model.verify_yang_baxter(value).status is CheckStatus.PASSED
    assert model.verify_yang_baxter(other).status is CheckStatus.FAILED
