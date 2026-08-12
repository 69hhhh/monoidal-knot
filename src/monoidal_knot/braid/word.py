"""Compact, typed braid words and expansion into morphism syntax trees."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from monoidal_knot.category.morphisms import CrossingSign, Morphism, braiding, identity
from monoidal_knot.category.objects import ObjectExpr
from monoidal_knot.errors import CategoryMismatchError, DefinitionError, MorphismTypeError

if TYPE_CHECKING:
    from monoidal_knot.braid.closure import FramedClosure


@dataclass(frozen=True, slots=True)
class BraidMorphism:
    """A colored braid represented by its top object word and braid generators.

    Generators are 1-based and are applied from top to bottom in tuple order.
    A positive ``i`` denotes ``sigma_i`` and a negative ``i`` denotes its
    inverse.  The empty word is the identity braid.
    """

    objects: ObjectExpr
    word: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.objects, ObjectExpr):
            raise DefinitionError("Braid objects must be an ObjectExpr.")
        if self.objects.is_unit:
            raise DefinitionError("A braid must have at least one strand.")
        if not isinstance(self.word, tuple):
            raise DefinitionError("A braid word must be stored as a tuple.")
        for generator in self.word:
            if type(generator) is not int:
                raise DefinitionError("Every braid generator must be an integer.")
            if not 1 <= abs(generator) < self.strands:
                raise DefinitionError(
                    "A braid generator index must satisfy "
                    f"1 <= abs(i) < {self.strands}; received {generator}."
                )

    @classmethod
    def identity(cls, objects: ObjectExpr) -> Self:
        """Return the identity braid on a nonempty tensor word."""

        return cls(objects)

    @property
    def dom(self) -> ObjectExpr:
        """The colored object word at the top of the braid."""

        return self.objects

    @property
    def cod(self) -> ObjectExpr:
        """The colored object word obtained at the bottom of the braid."""

        factors = list(self.objects.factors)
        for generator in self.word:
            index = abs(generator) - 1
            factors[index], factors[index + 1] = factors[index + 1], factors[index]
        return ObjectExpr(self.category_id, tuple(factors))

    @property
    def category_id(self) -> str:
        """The category containing the braid's colored objects."""

        return self.objects.category_id

    @property
    def strands(self) -> int:
        """The number of strands, derived from the top object word."""

        return len(self.objects.factors)

    @property
    def writhe(self) -> int:
        """Return the exponent sum of the braid word."""

        return sum(1 if generator > 0 else -1 for generator in self.word)

    def then(self, other: BraidMorphism) -> Self:
        """Place ``other`` below this braid and concatenate their words."""

        if self.category_id != other.category_id:
            raise CategoryMismatchError(
                "Cannot compose braids from different categories: "
                f"{self.category_id!r} and {other.category_id!r}."
            )
        if self.cod != other.dom:
            raise MorphismTypeError(
                "Cannot compose braids: the first codomain "
                f"{self.cod} does not equal the second domain {other.dom}."
            )
        return type(self)(self.dom, self.word + other.word)

    def inverse(self) -> Self:
        """Return the vertical inverse with reversed, negated generators."""

        return type(self)(self.cod, tuple(-generator for generator in reversed(self.word)))

    def expand(self) -> Morphism:
        """Expand every local crossing into the general typed morphism AST."""

        current = self.dom
        result = identity(current)
        for generator in self.word:
            index = abs(generator) - 1
            left = ObjectExpr(self.category_id, (current.factors[index],))
            right = ObjectExpr(self.category_id, (current.factors[index + 1],))
            sign = CrossingSign.POSITIVE if generator > 0 else CrossingSign.NEGATIVE
            crossing = braiding(left, right, sign=sign)

            prefix = ObjectExpr(self.category_id, current.factors[:index])
            suffix = ObjectExpr(self.category_id, current.factors[index + 2 :])
            local = identity(prefix).tensor(crossing).tensor(identity(suffix))
            result = result.then(local)
            current = local.cod

        return result

    def close(self) -> FramedClosure:
        """Form the abstract blackboard-framed closure of this braid."""

        from monoidal_knot.braid.closure import FramedClosure

        return FramedClosure(self)
