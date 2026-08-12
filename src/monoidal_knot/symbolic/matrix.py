"""Small immutable exact matrices over ``ScalarExpr``."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from monoidal_knot.errors import ExactMatrixError, NonInvertibleError, ScalarDomainError
from monoidal_knot.symbolic.base import ScalarExpr, ScalarInput, coerce_scalar
from monoidal_knot.symbolic.grassmann import GrassmannAlgebra
from monoidal_knot.symbolic.parity import Parity


@dataclass(frozen=True, slots=True, init=False, eq=False)
class ExactMatrix:
    """A nonempty immutable dense matrix with exact symbolic entries."""

    _algebra: GrassmannAlgebra | None
    _rows: tuple[tuple[ScalarExpr, ...], ...]

    def __init__(self, rows: Sequence[Sequence[ScalarInput]]) -> None:
        converted = tuple(tuple(coerce_scalar(value) for value in row) for row in rows)
        if not converted or not converted[0]:
            raise ExactMatrixError("An ExactMatrix must have at least one row and one column.")
        column_count = len(converted[0])
        if any(len(row) != column_count for row in converted):
            raise ExactMatrixError("Every ExactMatrix row must have the same length.")
        algebra: GrassmannAlgebra | None = None
        for row in converted:
            for value in row:
                if value.algebra is None:
                    continue
                if algebra is not None and algebra is not value.algebra:
                    raise ScalarDomainError(
                        "One ExactMatrix cannot mix different Grassmann algebra registries."
                    )
                algebra = value.algebra
        object.__setattr__(self, "_rows", converted)
        object.__setattr__(self, "_algebra", algebra)

    @property
    def rows(self) -> tuple[tuple[ScalarExpr, ...], ...]:
        """Return the immutable row-major entries."""

        return self._rows

    @property
    def shape(self) -> tuple[int, int]:
        """Return ``(row_count, column_count)``."""

        return len(self.rows), len(self.rows[0])

    @property
    def algebra(self) -> GrassmannAlgebra | None:
        """Return the matrix's Grassmann registry, if any."""

        return self._algebra

    @property
    def parity(self) -> Parity:
        """Classify the combined support of all entries."""

        entry_parities = {
            value.parity for row in self.rows for value in row if value.parity is not Parity.ZERO
        }
        if not entry_parities:
            return Parity.ZERO
        if entry_parities <= {Parity.EVEN}:
            return Parity.EVEN
        if entry_parities <= {Parity.ODD}:
            return Parity.ODD
        return Parity.MIXED

    @property
    def is_even(self) -> bool:
        """Whether every matrix entry is zero or even."""

        return all(value.is_even for row in self.rows for value in row)

    def non_even_entries(self) -> tuple[tuple[int, int, Parity], ...]:
        """Return zero-based positions and parities of odd or mixed entries."""

        return tuple(
            (row_index, column_index, value.parity)
            for row_index, row in enumerate(self.rows)
            for column_index, value in enumerate(row)
            if not value.is_even
        )

    def require_even_entries(self, *, context: str = "matrix") -> None:
        """Raise with precise positions unless all entries are even or zero."""

        invalid = self.non_even_entries()
        if invalid:
            details = ", ".join(
                f"({row}, {column})={parity.value}" for row, column, parity in invalid
            )
            raise ExactMatrixError(f"{context} requires even entries; found {details}.")

    def tensor(self, other: ExactMatrix) -> ExactMatrix:
        """Return the ordinary, non-Koszul Kronecker product."""

        rows: list[list[ScalarExpr]] = []
        for left_row in self.rows:
            for right_row in other.rows:
                rows.append([left * right for left in left_row for right in right_row])
        return ExactMatrix(rows)

    def __getitem__(self, key: tuple[int, int]) -> ScalarExpr:
        row, column = key
        return self.rows[row][column]

    def __add__(self, other: ExactMatrix) -> ExactMatrix:
        self._require_same_shape(other, operation="add")
        return ExactMatrix(
            [
                [left + right for left, right in zip(left_row, right_row, strict=True)]
                for left_row, right_row in zip(self.rows, other.rows, strict=True)
            ]
        )

    def __sub__(self, other: ExactMatrix) -> ExactMatrix:
        self._require_same_shape(other, operation="subtract")
        return ExactMatrix(
            [
                [left - right for left, right in zip(left_row, right_row, strict=True)]
                for left_row, right_row in zip(self.rows, other.rows, strict=True)
            ]
        )

    def __neg__(self) -> ExactMatrix:
        return ExactMatrix([[-value for value in row] for row in self.rows])

    def __mul__(self, scalar: ScalarInput) -> ExactMatrix:
        factor = coerce_scalar(scalar)
        return ExactMatrix([[value * factor for value in row] for row in self.rows])

    def __rmul__(self, scalar: ScalarInput) -> ExactMatrix:
        factor = coerce_scalar(scalar)
        return ExactMatrix([[factor * value for value in row] for row in self.rows])

    def __matmul__(self, other: ExactMatrix) -> ExactMatrix:
        if self.shape[1] != other.shape[0]:
            raise ExactMatrixError(
                f"Cannot multiply matrices with shapes {self.shape} and {other.shape}."
            )
        rows: list[list[ScalarExpr]] = []
        for row_index in range(self.shape[0]):
            row: list[ScalarExpr] = []
            for column_index in range(other.shape[1]):
                value = ScalarExpr()
                for inner_index in range(self.shape[1]):
                    value += self[row_index, inner_index] * other[inner_index, column_index]
                row.append(value)
            rows.append(row)
        return ExactMatrix(rows)

    def trace(self) -> ScalarExpr:
        """Return the ordinary exact trace of a square matrix."""

        if self.shape[0] != self.shape[1]:
            raise ExactMatrixError(
                f"Cannot take the trace of a nonsquare matrix with shape {self.shape}."
            )
        result = ScalarExpr()
        for index in range(self.shape[0]):
            result += self[index, index]
        return result

    def inverse(self) -> ExactMatrix:
        """Return the exact inverse using Gauss--Jordan elimination.

        The first version only implements ordinary even matrices.  Supporting
        odd matrix entries would require graded bases and Koszul signs.
        """

        if self.shape[0] != self.shape[1]:
            raise ExactMatrixError(f"Cannot invert a nonsquare matrix with shape {self.shape}.")
        self.require_even_entries(context="matrix inversion")
        size = self.shape[0]
        augmented = [
            list(row) + [ScalarExpr(int(row_index == column_index)) for column_index in range(size)]
            for row_index, row in enumerate(self.rows)
        ]

        for column in range(size):
            pivot_row: int | None = None
            pivot_inverse: ScalarExpr | None = None
            for candidate in range(column, size):
                try:
                    inverse = augmented[candidate][column].inverse()
                except NonInvertibleError:
                    continue
                pivot_row = candidate
                pivot_inverse = inverse
                break
            if pivot_row is None or pivot_inverse is None:
                raise NonInvertibleError(
                    f"The exact matrix is singular or has no invertible pivot in column {column}."
                )
            if pivot_row != column:
                augmented[column], augmented[pivot_row] = (
                    augmented[pivot_row],
                    augmented[column],
                )

            augmented[column] = [value * pivot_inverse for value in augmented[column]]
            for row_index in range(size):
                if row_index == column:
                    continue
                factor = augmented[row_index][column]
                if factor.is_zero:
                    continue
                augmented[row_index] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(
                        augmented[row_index], augmented[column], strict=True
                    )
                ]

        return ExactMatrix([row[size:] for row in augmented])

    def _require_same_shape(self, other: ExactMatrix, *, operation: str) -> None:
        if self.shape != other.shape:
            raise ExactMatrixError(
                f"Cannot {operation} matrices with shapes {self.shape} and {other.shape}."
            )

    @classmethod
    def zeros(cls, row_count: int, column_count: int) -> ExactMatrix:
        """Construct a positive-size zero matrix."""

        _require_positive_size(row_count, column_count)
        return cls([[0 for _ in range(column_count)] for _ in range(row_count)])

    @classmethod
    def identity(cls, size: int) -> ExactMatrix:
        """Construct a positive-size identity matrix."""

        _require_positive_size(size, size)
        return cls([[int(row == column) for column in range(size)] for row in range(size)])

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ExactMatrix) and self.rows == other.rows

    def __hash__(self) -> int:
        return hash(self.rows)

    def __repr__(self) -> str:
        return f"ExactMatrix({self.rows!r})"


def _require_positive_size(row_count: int, column_count: int) -> None:
    if (
        not isinstance(row_count, int)
        or isinstance(row_count, bool)
        or not isinstance(column_count, int)
        or isinstance(column_count, bool)
        or row_count <= 0
        or column_count <= 0
    ):
        raise ExactMatrixError("ExactMatrix dimensions must be positive integers.")
