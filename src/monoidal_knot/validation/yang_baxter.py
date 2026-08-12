"""Exact residuals for the braid and quantum Yang--Baxter equations."""

from __future__ import annotations

from monoidal_knot.errors import DefinitionError
from monoidal_knot.symbolic import ExactMatrix


def braid_yang_baxter_residual(check_r: ExactMatrix, *, dimension: int) -> ExactMatrix:
    """Return ``R12 R23 R12 - R23 R12 R23`` for a homogeneous ``check_R``."""

    _require_square_r(check_r, dimension=dimension)
    identity = ExactMatrix.identity(dimension)
    r12 = check_r.tensor(identity)
    r23 = identity.tensor(check_r)
    return r12 @ r23 @ r12 - r23 @ r12 @ r23


def quantum_yang_baxter_residual(quantum_r: ExactMatrix, *, dimension: int) -> ExactMatrix:
    """Return ``R12 R13 R23 - R23 R13 R12`` for a homogeneous quantum ``R``."""

    _require_square_r(quantum_r, dimension=dimension)
    identity = ExactMatrix.identity(dimension)
    swap = tensor_swap(dimension, dimension)
    swap_23 = identity.tensor(swap)
    r12 = quantum_r.tensor(identity)
    r23 = identity.tensor(quantum_r)
    r13 = swap_23 @ r12 @ swap_23
    return r12 @ r13 @ r23 - r23 @ r13 @ r12


def check_to_quantum(check_r: ExactMatrix, *, dimension: int) -> ExactMatrix:
    """Convert ``check_R = P R`` back to the quantum ``R = P check_R`` convention."""

    _require_square_r(check_r, dimension=dimension)
    return tensor_swap(dimension, dimension) @ check_r


def tensor_swap(left_dimension: int, right_dimension: int) -> ExactMatrix:
    """Return the exact tensor-factor permutation in the package basis order."""

    if (
        type(left_dimension) is not int
        or type(right_dimension) is not int
        or left_dimension <= 0
        or right_dimension <= 0
    ):
        raise DefinitionError("Tensor-swap dimensions must be positive integers.")
    size = left_dimension * right_dimension
    rows = [[0 for _ in range(size)] for _ in range(size)]
    for left_index in range(left_dimension):
        for right_index in range(right_dimension):
            source = left_index * right_dimension + right_index
            target = right_index * left_dimension + left_index
            rows[target][source] = 1
    return ExactMatrix(rows)


def _require_square_r(matrix: ExactMatrix, *, dimension: int) -> None:
    if not isinstance(matrix, ExactMatrix):
        raise DefinitionError("A Yang--Baxter matrix must be an ExactMatrix.")
    if type(dimension) is not int or dimension <= 0:
        raise DefinitionError("A Yang--Baxter object dimension must be positive.")
    expected = (dimension**2, dimension**2)
    if matrix.shape != expected:
        raise DefinitionError(
            f"A Yang--Baxter matrix for dimension {dimension} must have shape {expected}; "
            f"received {matrix.shape}."
        )
