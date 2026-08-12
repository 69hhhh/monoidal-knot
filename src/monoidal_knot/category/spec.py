"""Minimal category signature and factories for stage 1."""

from __future__ import annotations

from dataclasses import dataclass

from monoidal_knot.category.morphisms import (
    CrossingSign,
    DualPosition,
    Morphism,
    braiding,
    coevaluation,
    coupon,
    evaluation,
    identity,
    twist,
)
from monoidal_knot.category.objects import ObjectExpr, ObjectFactor
from monoidal_knot.errors import CategoryMismatchError, DefinitionError


@dataclass(frozen=True, slots=True)
class CategorySpec:
    """A strict pivotal ribbon category signature.

    The stable ``id`` is the semantic category identity used by object and
    morphism expressions.  Stage 1 deliberately has no scalar domain,
    relation registry, or capability flags.
    """

    id: str
    name: str | None = None

    def __post_init__(self) -> None:
        if not self.id or self.id.isspace():
            raise DefinitionError("A category identifier must be non-empty.")
        if self.name is not None and (not self.name or self.name.isspace()):
            raise DefinitionError("A category name, when provided, must be non-empty.")

    @property
    def unit(self) -> ObjectExpr:
        """Return the unit object, represented by the empty tensor word."""

        return ObjectExpr(self.id)

    def object(self, generator_id: str) -> ObjectExpr:
        """Return a generating object in this category."""

        return ObjectExpr(self.id, (ObjectFactor(generator_id),))

    def identity(self, object_expr: ObjectExpr) -> Morphism:
        """Return the identity of an object in this category."""

        self._require_object(object_expr)
        return identity(object_expr)

    def coupon(self, coupon_id: str, dom: ObjectExpr, cod: ObjectExpr) -> Morphism:
        """Declare an arbitrary typed coupon ``dom -> cod``."""

        self._require_object(dom)
        self._require_object(cod)
        return coupon(coupon_id, dom, cod)

    def braiding(
        self,
        left: ObjectExpr,
        right: ObjectExpr,
        *,
        sign: CrossingSign = CrossingSign.POSITIVE,
    ) -> Morphism:
        """Return a positive or negative colored crossing."""

        self._require_object(left)
        self._require_object(right)
        return braiding(left, right, sign=sign)

    def evaluation(self, object_expr: ObjectExpr, *, dual_position: DualPosition) -> Morphism:
        """Return a cap with its full type fixed by ``dual_position``."""

        self._require_object(object_expr)
        return evaluation(object_expr, dual_position=dual_position)

    def coevaluation(self, object_expr: ObjectExpr, *, dual_position: DualPosition) -> Morphism:
        """Return a cup with its full type fixed by ``dual_position``."""

        self._require_object(object_expr)
        return coevaluation(object_expr, dual_position=dual_position)

    def twist(self, object_expr: ObjectExpr, *, inverse: bool = False) -> Morphism:
        """Return a twist or inverse twist of an object."""

        self._require_object(object_expr)
        return twist(object_expr, inverse=inverse)

    def _require_object(self, object_expr: ObjectExpr) -> None:
        if object_expr.category_id != self.id:
            raise CategoryMismatchError(
                f"Object belongs to category {object_expr.category_id!r}, not {self.id!r}."
            )
