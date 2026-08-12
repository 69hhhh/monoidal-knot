from monoidal_knot.conventions import (
    DEFAULT_CONVENTIONS,
    BraidWordOrder,
    CompositionOrder,
    PositiveCrossingImage,
    TensorBasisOrder,
    VectorAction,
)


def test_default_conventions_are_versioned_and_explicit() -> None:
    assert DEFAULT_CONVENTIONS.version == 1
    assert DEFAULT_CONVENTIONS.vector_action is VectorAction.COLUMN
    assert DEFAULT_CONVENTIONS.composition_order is CompositionOrder.SELF_THEN_OTHER
    assert (
        DEFAULT_CONVENTIONS.tensor_basis_order is TensorBasisOrder.LEXICOGRAPHIC_RIGHTMOST_FASTEST
    )
    assert DEFAULT_CONVENTIONS.braid_word_order is BraidWordOrder.TOP_TO_BOTTOM
    assert DEFAULT_CONVENTIONS.positive_crossing_image is PositiveCrossingImage.CHECK_R
    assert DEFAULT_CONVENTIONS.strand_index_base == 1
