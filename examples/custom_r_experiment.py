"""Define a custom R matrix, evaluate a closure, and save an audit record."""

from pathlib import Path

from monoidal_knot import (
    BraidMorphism,
    CategorySpec,
    ExactMatrix,
    ExperimentRecord,
    MarkovTraceParameters,
    QuantumTrace,
    RMatrixFunctor,
    RMatrixSpec,
    save,
)

category = CategorySpec("custom-swap")
obj = category.object("V")
check_r = ExactMatrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
spec = RMatrixSpec(check_r, convention="check")
trace = QuantumTrace(
    {obj: ExactMatrix.identity(2)},
    parameters=MarkovTraceParameters(alpha=1, beta=1),
)
model = RMatrixFunctor(
    source=category,
    object_map={obj: 2},
    r_matrices={(obj, obj): spec},
    trace_data=trace,
)
braid = BraidMorphism(obj.tensor_power(2), (1,))
result = model.evaluate_invariant(braid.close())
record = ExperimentRecord(
    category=category,
    braid=braid,
    r_matrices=((obj, obj, spec),),
    trace_data=trace,
    validation=result.report,
    raw_value=result.raw_value,
    normalized_value=result.normalized_value,
    metadata={"description": "two-strand swap closure"},
)
output = Path("custom-r-experiment.json")
save(record, output)
print(f"status={result.report.status.value}")
print(f"raw={result.raw_value}, normalized={result.normalized_value}")
print(f"saved={output.resolve()}")
