"""Machine-readable identifiers for the package's stable conventions."""

from dataclasses import dataclass
from enum import StrEnum


class VectorAction(StrEnum):
    """How matrices act on coordinate vectors."""

    COLUMN = "column"


class CompositionOrder(StrEnum):
    """Meaning of the public ``then`` operation."""

    SELF_THEN_OTHER = "self-then-other"


class TensorBasisOrder(StrEnum):
    """Flattening order for a tensor-product basis."""

    LEXICOGRAPHIC_RIGHTMOST_FASTEST = "lexicographic-rightmost-fastest"


class BraidWordOrder(StrEnum):
    """Reading direction for braid word entries."""

    TOP_TO_BOTTOM = "top-to-bottom"


class PositiveCrossingImage(StrEnum):
    """Matrix assigned to a positive Artin generator."""

    CHECK_R = "check-r"


@dataclass(frozen=True, slots=True)
class ConventionSpec:
    """Versioned conventions that affect evaluation and serialization."""

    version: int
    vector_action: VectorAction
    composition_order: CompositionOrder
    tensor_basis_order: TensorBasisOrder
    braid_word_order: BraidWordOrder
    positive_crossing_image: PositiveCrossingImage
    strand_index_base: int


DEFAULT_CONVENTIONS = ConventionSpec(
    version=1,
    vector_action=VectorAction.COLUMN,
    composition_order=CompositionOrder.SELF_THEN_OTHER,
    tensor_basis_order=TensorBasisOrder.LEXICOGRAPHIC_RIGHTMOST_FASTEST,
    braid_word_order=BraidWordOrder.TOP_TO_BOTTOM,
    positive_crossing_image=PositiveCrossingImage.CHECK_R,
    strand_index_base=1,
)
