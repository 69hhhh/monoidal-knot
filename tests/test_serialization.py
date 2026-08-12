import json

import pytest

from monoidal_knot import (
    BraidMorphism,
    CategorySpec,
    ExactMatrix,
    ExperimentRecord,
    GrassmannAlgebra,
    MarkovTraceParameters,
    QuantumTrace,
    RMatrixFunctor,
    RMatrixSpec,
    SerializationError,
    dumps,
    loads,
    save,
)


def test_category_object_morphism_and_braid_round_trip() -> None:
    category = CategorySpec("round-trip", "Round trip")
    left = category.object("V")
    right = category.object("W")
    values = (
        category,
        left.tensor(right.dual),
        category.braiding(left, right).then(category.braiding(right, left)),
        BraidMorphism(left.tensor_power(3), (1, -2, 1)),
    )
    for value in values:
        assert loads(dumps(value)) == value


def test_grassmann_matrix_round_trip_shares_one_registry() -> None:
    algebra = GrassmannAlgebra("G")
    theta, eta = algebra.symbols("theta", "eta")
    matrix = ExactMatrix([[1 + theta * eta, 0], [0, 1]])
    restored = loads(dumps(matrix))
    assert isinstance(restored, ExactMatrix)
    assert str(restored) == str(matrix)
    assert restored[0, 0].algebra is not algebra


def test_complete_experiment_round_trip_and_file_save(tmp_path) -> None:
    category = CategorySpec("experiment")
    obj = category.object("V")
    swap = ExactMatrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
    spec = RMatrixSpec(swap)
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
        category,
        braid,
        ((obj, obj, spec),),
        trace,
        result.report,
        result.raw_value,
        result.normalized_value,
        {"purpose": "test"},
    )
    path = tmp_path / "experiment.json"
    save(record, path)
    restored = loads(path.read_text(encoding="utf-8"))
    assert isinstance(restored, ExperimentRecord)
    assert restored.braid == braid
    assert restored.validation.status == record.validation.status
    assert restored.raw_value == record.raw_value
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1


def test_unknown_schema_version_is_rejected() -> None:
    document = json.loads(dumps(CategorySpec("C")))
    document["version"] = 999
    with pytest.raises(SerializationError, match="version"):
        loads(json.dumps(document))
