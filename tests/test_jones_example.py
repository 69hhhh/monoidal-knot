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
    Symbol,
)


def jones_model() -> tuple[RMatrixFunctor, object, object]:
    q = Symbol("q", nonzero=True)
    category = CategorySpec("jones-test")
    value = category.object("V")
    check_r = ExactMatrix(
        [
            [q, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 1, q - q**-1, 0],
            [0, 0, 0, q],
        ]
    )
    mu = ExactMatrix([[q, 0], [0, q**-1]])
    parameters = MarkovTraceParameters(
        alpha=q**2,
        beta=1,
        overall_scale=1 / (q + q**-1),
    )
    model = RMatrixFunctor(
        source=category,
        object_map={value: 2},
        r_matrices={(value, value): RMatrixSpec(check_r)},
        trace_data=QuantumTrace({value: mu}, parameters=parameters),
    )
    return model, value, q


def test_jones_data_passes_both_ybe_and_markov_trace_checks() -> None:
    model, _, _ = jones_model()

    report = model.verify()

    assert report.status is CheckStatus.PASSED
    assert report.verified
    assert (
        next(check for check in report.checks if check.key == "ybe.0.braid").status
        is CheckStatus.PASSED
    )
    assert (
        next(check for check in report.checks if check.key == "ybe.0.quantum").status
        is CheckStatus.PASSED
    )


def test_jones_unknot_and_positive_stabilization_both_normalize_to_one() -> None:
    model, value, _ = jones_model()
    one_strand = BraidMorphism.identity(value)
    stabilized = BraidMorphism(value.tensor_power(2), (1,))

    first = model.evaluate_invariant(one_strand.close())
    second = model.evaluate_invariant(stabilized.close())

    assert first.normalized_value == 1
    assert second.normalized_value == 1
    assert first.classification is EvaluationClassification.VERIFIED_INVARIANT
    assert second.classification is EvaluationClassification.VERIFIED_INVARIANT


def test_jones_unlink_hopf_link_and_right_trefoil_values() -> None:
    model, value, q = jones_model()
    two_strands = value.tensor_power(2)
    unlink = BraidMorphism.identity(two_strands)
    positive_hopf = BraidMorphism(two_strands, (1, 1))
    right_trefoil = BraidMorphism(two_strands, (1, 1, 1))

    unlink_value = model.evaluate_invariant(unlink.close()).normalized_value
    hopf_value = model.evaluate_invariant(positive_hopf.close()).normalized_value
    trefoil_value = model.evaluate_invariant(right_trefoil.close()).normalized_value

    assert unlink_value == q + q**-1
    assert hopf_value == q**-1 + q**-5
    # With t = q**-2, this is the standard convention V_right-trefoil(t)=t+t**3-t**4.
    assert trefoil_value == q**-2 + q**-6 - q**-8
