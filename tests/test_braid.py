import pytest

from monoidal_knot import (
    BraidingNode,
    BraidMorphism,
    CategoryMismatchError,
    CategorySpec,
    ComposeNode,
    CrossingSign,
    DefinitionError,
    FramedClosure,
    IdentityNode,
    MorphismTypeError,
    TensorNode,
)


def test_braid_word_is_strictly_validated() -> None:
    category = CategorySpec("braid-validation")
    value = category.object("V")
    three_strands = value.tensor_power(3)

    with pytest.raises(DefinitionError, match="at least one strand"):
        BraidMorphism(category.unit)
    with pytest.raises(DefinitionError, match="stored as a tuple"):
        BraidMorphism(three_strands, [1])  # type: ignore[arg-type]
    with pytest.raises(DefinitionError, match="must be an integer"):
        BraidMorphism(three_strands, (True,))
    with pytest.raises(DefinitionError, match=r"1 <= abs\(i\) < 3"):
        BraidMorphism(three_strands, (0,))
    with pytest.raises(DefinitionError, match=r"1 <= abs\(i\) < 3"):
        BraidMorphism(three_strands, (-3,))


def test_colored_braid_computes_its_bottom_object_word() -> None:
    category = CategorySpec("colored-braid-word")
    red = category.object("red")
    green = category.object("green")
    blue = category.object("blue")
    objects = red.tensor(green).tensor(blue)

    braid = BraidMorphism(objects, (1, -2, 1))

    assert braid.dom == objects
    assert braid.cod == blue.tensor(green).tensor(red)
    assert braid.strands == 3
    assert braid.category_id == category.id


def test_identity_composition_inverse_and_writhe_are_structural() -> None:
    category = CategorySpec("braid-operations")
    a = category.object("A")
    b = category.object("B")
    c = category.object("C")
    objects = a.tensor(b).tensor(c)
    first = BraidMorphism(objects, (1, -2))
    second = BraidMorphism(first.cod, (1,))

    identity = BraidMorphism.identity(objects)
    composite = first.then(second)
    inverse = composite.inverse()

    assert identity.word == ()
    assert identity.dom == identity.cod == objects
    assert identity.writhe == 0
    assert identity.then(first) == first
    assert composite.word == (1, -2, 1)
    assert composite.writhe == 1
    assert inverse.dom == composite.cod
    assert inverse.cod == composite.dom
    assert inverse.word == (-1, 2, -1)
    assert inverse.inverse() == composite


def test_braid_composition_checks_category_and_colored_boundary() -> None:
    first_category = CategorySpec("first-braid-category")
    second_category = CategorySpec("second-braid-category")
    a = first_category.object("A")
    b = first_category.object("B")
    first = BraidMorphism(a.tensor(b), (1,))

    with pytest.raises(MorphismTypeError, match="first codomain"):
        first.then(BraidMorphism(a.tensor(b)))
    with pytest.raises(CategoryMismatchError, match="different categories"):
        first.then(BraidMorphism(second_category.object("V")))


def test_expansion_uses_local_colored_crossings_and_general_ast_nodes() -> None:
    category = CategorySpec("braid-expansion")
    a = category.object("A")
    b = category.object("B")
    c = category.object("C")
    braid = BraidMorphism(a.tensor(b).tensor(c), (1, -2, 1))

    expanded = braid.expand()

    assert expanded.dom == braid.dom
    assert expanded.cod == braid.cod
    assert isinstance(expanded.node, ComposeNode)
    assert len(expanded.node.morphisms) == 3

    first_step = expanded.node.morphisms[0]
    second_step = expanded.node.morphisms[1]
    assert isinstance(first_step.node, TensorNode)
    assert isinstance(first_step.node.morphisms[0].node, BraidingNode)
    assert first_step.node.morphisms[0].node.left == a
    assert first_step.node.morphisms[0].node.right == b
    assert first_step.node.morphisms[0].node.sign is CrossingSign.POSITIVE
    assert isinstance(second_step.node, TensorNode)
    assert isinstance(second_step.node.morphisms[1].node, BraidingNode)
    assert second_step.node.morphisms[1].node.left == a
    assert second_step.node.morphisms[1].node.right == c
    assert second_step.node.morphisms[1].node.sign is CrossingSign.NEGATIVE


def test_identity_expands_to_identity_and_braid_relation_sides_are_constructible() -> None:
    category = CategorySpec("braid-relation-structure")
    value = category.object("V")
    objects = value.tensor_power(3)
    identity = BraidMorphism.identity(objects).expand()
    left = BraidMorphism(objects, (1, 2, 1)).expand()
    right = BraidMorphism(objects, (2, 1, 2)).expand()

    assert isinstance(identity.node, IdentityNode)
    assert identity.dom == identity.cod == objects
    assert left.dom == right.dom == objects
    assert left.cod == right.cod == objects
    assert left != right


def test_framed_closure_requires_compatible_colors_and_keeps_blackboard_writhe() -> None:
    category = CategorySpec("framed-closure")
    value = category.object("V")
    braid = BraidMorphism(value.tensor_power(3), (1, -2, 1))

    closure = braid.close()

    assert isinstance(closure, FramedClosure)
    assert closure.braid == braid
    assert closure.category_id == category.id
    assert closure.writhe == braid.writhe == 1

    red = category.object("red")
    blue = category.object("blue")
    with pytest.raises(MorphismTypeError, match="equal top and bottom"):
        FramedClosure(BraidMorphism(red.tensor(blue), (1,)))
