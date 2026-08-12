"""Complete stage-5 Jones example with explicit conventions and validation."""

from monoidal_knot import (
    BraidMorphism,
    CategorySpec,
    ExactMatrix,
    MarkovTraceParameters,
    QuantumTrace,
    RMatrixFunctor,
    RMatrixSpec,
    Symbol,
)

q = Symbol("q", nonzero=True)
category = CategorySpec("jones-example")
V = category.object("V")

# Positive braid generator, in basis (00, 01, 10, 11).
check_r = ExactMatrix(
    [
        [q, 0, 0, 0],
        [0, 0, 1, 0],
        [0, 1, q - q**-1, 0],
        [0, 0, 0, q],
    ]
)
mu = ExactMatrix([[q, 0], [0, q**-1]])

# Enhanced Yang--Baxter normalization:
#   V(b-hat) = (q + q^-1)^-1 q^(-2 writhe(b)) Tr(mu^tensor-n rho(b)).
# Thus V(unknot)=1.  With t=q^-2, the right trefoil is t+t^3-t^4.
parameters = MarkovTraceParameters(
    alpha=q**2,
    beta=1,
    overall_scale=1 / (q + q**-1),
)
model = RMatrixFunctor(
    source=category,
    object_map={V: 2},
    r_matrices={(V, V): RMatrixSpec(check_r, convention="check")},
    trace_data=QuantumTrace({V: mu}, parameters=parameters),
)

examples = {
    "unknot": BraidMorphism.identity(V),
    "two_component_unlink": BraidMorphism.identity(V.tensor_power(2)),
    "positive_hopf_link": BraidMorphism(V.tensor_power(2), (1, 1)),
    "right_trefoil": BraidMorphism(V.tensor_power(2), (1, 1, 1)),
}


if __name__ == "__main__":
    report = model.verify()
    print(f"validation: {report.status.value} ({len(report.checks)} exact checks)")
    for name, braid in examples.items():
        result = model.evaluate_invariant(braid.close())
        print(
            f"{name}: writhe={braid.writhe}, raw={result.raw_value}, "
            f"normalized={result.normalized_value}, status={result.classification.value}"
        )
