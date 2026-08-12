"""Diagnose an invalid label and a semantically wrong R convention."""

from monoidal_knot import (
    BraidMorphism,
    CategorySpec,
    DefinitionError,
    ExactMatrix,
    RMatrixFunctor,
    RMatrixSpec,
)

category = CategorySpec("convention-diagnostic")
obj = category.object("V")
check_r = ExactMatrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])

try:
    RMatrixSpec(check_r, convention="unchecked")
except DefinitionError as error:
    print(f"invalid label: {error}")

# A valid label can still be semantically wrong. Mislabeling the swap check_R
# as quantum R converts it to P @ R = identity. YBE still passes, so compare
# the evaluated generator with the operator the experiment intended to supply.
wrong_model = RMatrixFunctor(
    source=category,
    object_map={obj: 2},
    r_matrices={(obj, obj): RMatrixSpec(check_r, convention="quantum")},
)
generator = BraidMorphism(obj.tensor_power(2), (1,))
actual = wrong_model.evaluate_braid(generator)
print(f"YBE status alone: {wrong_model.verify_yang_baxter(obj).status.value}")
print(f"intended check_R equals evaluated generator: {actual == check_r}")
print("fix: this input is a braid operator, so use convention='check'")
