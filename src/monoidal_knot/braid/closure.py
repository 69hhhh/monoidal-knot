"""Abstract blackboard-framed closures of colored braids."""

from __future__ import annotations

from dataclasses import dataclass

from monoidal_knot.braid.word import BraidMorphism
from monoidal_knot.errors import DefinitionError, MorphismTypeError


@dataclass(frozen=True, slots=True)
class FramedClosure:
    """A colored braid closure retaining blackboard framing.

    This stage records closure structure only.  It does not choose trace data,
    apply a writhe correction, evaluate a matrix, or claim an invariant.
    """

    braid: BraidMorphism

    def __post_init__(self) -> None:
        if not isinstance(self.braid, BraidMorphism):
            raise DefinitionError("A framed closure must contain a BraidMorphism.")
        if self.braid.dom != self.braid.cod:
            raise MorphismTypeError(
                "A colored framed closure requires equal top and bottom object words; "
                f"received {self.braid.dom} and {self.braid.cod}."
            )

    @property
    def category_id(self) -> str:
        """The category containing the closed braid."""

        return self.braid.category_id

    @property
    def writhe(self) -> int:
        """The uncorrected writhe retained by blackboard framing."""

        return self.braid.writhe
