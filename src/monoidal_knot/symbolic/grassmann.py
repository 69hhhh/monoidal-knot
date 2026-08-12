"""Explicit Grassmann generator registries and bitset monomials."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from monoidal_knot.errors import DefinitionError, ScalarDomainError
from monoidal_knot.symbolic.parity import Parity

if TYPE_CHECKING:
    from monoidal_knot.symbolic.base import ScalarExpr


class GrassmannAlgebra:
    """An append-only, explicitly named registry of Grassmann generators.

    Algebra compatibility is based on object identity.  Reusing a textual ID
    does not silently merge independently constructed registries.
    """

    __slots__ = ("_id", "_indices", "_names")

    def __init__(self, algebra_id: str) -> None:
        if not isinstance(algebra_id, str) or not algebra_id or algebra_id.isspace():
            raise DefinitionError("A Grassmann algebra identifier must be non-empty.")
        self._id = algebra_id
        self._indices: dict[str, int] = {}
        self._names: list[str] = []

    @property
    def id(self) -> str:
        """Return the user-visible algebra identifier."""

        return self._id

    @property
    def generator_names(self) -> tuple[str, ...]:
        """Return generator names in their stable bit-index order."""

        return tuple(self._names)

    @property
    def generator_count(self) -> int:
        """Return the number of registered generators."""

        return len(self._names)

    def symbol(self, name: str) -> ScalarExpr:
        """Register or retrieve one odd generator as a scalar expression."""

        from monoidal_knot.symbolic.base import ScalarExpr

        index = self._register(name)
        return ScalarExpr._from_generator(self, index)

    def symbols(self, *names: str) -> tuple[ScalarExpr, ...]:
        """Register or retrieve several odd generators in the given order."""

        return tuple(self.symbol(name) for name in names)

    def monomial(self, mask: int) -> GrassmannMonomial:
        """Construct a validated bitset monomial in this algebra."""

        return GrassmannMonomial(self, mask)

    def _register(self, name: str) -> int:
        if not isinstance(name, str) or not name or name.isspace():
            raise DefinitionError("A Grassmann generator name must be non-empty.")
        if name in self._indices:
            return self._indices[name]
        index = len(self._names)
        self._indices[name] = index
        self._names.append(name)
        return index

    def __repr__(self) -> str:
        return f"GrassmannAlgebra({self.id!r}, generators={self.generator_names!r})"


@dataclass(frozen=True, slots=True, init=False, eq=False)
class GrassmannMonomial:
    """A square-free ordered Grassmann monomial stored as a nonnegative bitset."""

    _algebra: GrassmannAlgebra
    _mask: int

    def __init__(self, algebra: GrassmannAlgebra, mask: int) -> None:
        if not isinstance(algebra, GrassmannAlgebra):
            raise DefinitionError("A Grassmann monomial requires a GrassmannAlgebra.")
        if not isinstance(mask, int) or isinstance(mask, bool) or mask < 0:
            raise DefinitionError("A Grassmann monomial mask must be a nonnegative integer.")
        if mask.bit_length() > algebra.generator_count:
            raise DefinitionError("A Grassmann monomial mask references an unregistered generator.")
        object.__setattr__(self, "_algebra", algebra)
        object.__setattr__(self, "_mask", mask)

    @property
    def algebra(self) -> GrassmannAlgebra:
        """Return the registry that assigns meanings to the bits."""

        return self._algebra

    @property
    def mask(self) -> int:
        """Return the underlying bitset."""

        return self._mask

    @property
    def degree(self) -> int:
        """Return the number of generators in the monomial."""

        return self.mask.bit_count()

    @property
    def parity(self) -> Parity:
        """Return EVEN for even degree and ODD for odd degree."""

        return Parity.EVEN if self.degree % 2 == 0 else Parity.ODD

    @property
    def names(self) -> tuple[str, ...]:
        """Return generator names in canonical increasing-index order."""

        registry_names = self.algebra.generator_names
        return tuple(registry_names[index] for index in self.indices())

    def indices(self) -> Iterator[int]:
        """Yield set-bit indices in increasing order."""

        remaining = self.mask
        while remaining:
            lowest = remaining & -remaining
            yield lowest.bit_length() - 1
            remaining ^= lowest

    def multiply(self, other: GrassmannMonomial) -> tuple[int, GrassmannMonomial | None]:
        """Return ``(sign, product)``; a repeated generator gives ``(0, None)``."""

        if self.algebra is not other.algebra:
            raise ScalarDomainError(
                "Cannot multiply monomials from different Grassmann algebra registries."
            )
        if self.mask & other.mask:
            return 0, None
        swaps = 0
        for index in self.indices():
            swaps += (other.mask & ((1 << index) - 1)).bit_count()
        sign = -1 if swaps % 2 else 1
        return sign, GrassmannMonomial(self.algebra, self.mask | other.mask)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, GrassmannMonomial)
            and self.algebra is other.algebra
            and self.mask == other.mask
        )

    def __hash__(self) -> int:
        return hash((id(self.algebra), self.mask))

    def __str__(self) -> str:
        return "1" if self.mask == 0 else "*".join(self.names)

    def __repr__(self) -> str:
        return f"GrassmannMonomial({self.algebra.id!r}, mask={self.mask:#b})"
