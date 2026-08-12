import pytest

from monoidal_knot import (
    BraidingNode,
    CategoryMismatchError,
    CategorySpec,
    CoevaluationNode,
    ComposeNode,
    CrossingSign,
    DefinitionError,
    DualPosition,
    EvaluationNode,
    IdentityNode,
    Morphism,
    MorphismTypeError,
    TensorNode,
    TwistNode,
)


def test_coupon_accepts_arbitrary_tensor_word_types() -> None:
    category = CategorySpec("coupons")
    a = category.object("A")
    b = category.object("B")
    c = category.object("C")

    coupon = category.coupon("merge", a.tensor(b), c)

    assert coupon.dom == a.tensor(b)
    assert coupon.cod == c
    assert coupon.category_id == category.id


def test_typed_composition_flattens_and_eliminates_identities() -> None:
    category = CategorySpec("composition")
    a = category.object("A")
    b = category.object("B")
    c = category.object("C")
    d = category.object("D")
    f = category.coupon("f", a, b)
    g = category.coupon("g", b, c)
    h = category.coupon("h", c, d)

    left_associated = f.then(g).then(h)
    right_associated = f.then(g.then(h))

    assert left_associated == right_associated
    assert isinstance(left_associated.node, ComposeNode)
    assert left_associated.node.morphisms == (f, g, h)
    assert category.identity(a).then(f) == f
    assert f.then(category.identity(b)) == f
    assert hash(left_associated) == hash(right_associated)


def test_illegal_composition_is_rejected_at_construction() -> None:
    category = CategorySpec("composition-errors")
    a = category.object("A")
    b = category.object("B")
    c = category.object("C")
    f = category.coupon("f", a, b)
    g = category.coupon("g", c, a)

    with pytest.raises(MorphismTypeError, match="first codomain"):
        f.then(g)


def test_manually_assembled_node_must_match_its_declared_type() -> None:
    category = CategorySpec("manual-node")
    a = category.object("A")
    b = category.object("B")

    with pytest.raises(MorphismTypeError, match="identity"):
        Morphism(a, b, IdentityNode())
    with pytest.raises(DefinitionError, match="tuple"):
        ComposeNode([])  # type: ignore[arg-type]


def test_tensor_is_typed_flattened_and_has_unit_identity() -> None:
    category = CategorySpec("tensor")
    a = category.object("A")
    b = category.object("B")
    c = category.object("C")
    x = category.object("X")
    y = category.object("Y")
    z = category.object("Z")
    f = category.coupon("f", a, x)
    g = category.coupon("g", b, y)
    h = category.coupon("h", c, z)

    left_associated = f.tensor(g).tensor(h)
    right_associated = f.tensor(g.tensor(h))

    assert left_associated == right_associated
    assert isinstance(left_associated.node, TensorNode)
    assert left_associated.node.morphisms == (f, g, h)
    assert left_associated.dom == a.tensor(b).tensor(c)
    assert left_associated.cod == x.tensor(y).tensor(z)
    assert category.identity(category.unit).tensor(f) == f
    assert f.tensor(category.identity(category.unit)) == f


def test_positive_and_negative_colored_crossings_have_displayed_types() -> None:
    category = CategorySpec("colored-braid")
    red = category.object("red")
    blue = category.object("blue")

    positive = category.braiding(red, blue)
    negative = category.braiding(red, blue, sign=CrossingSign.NEGATIVE)

    for crossing in (positive, negative):
        assert crossing.dom == red.tensor(blue)
        assert crossing.cod == blue.tensor(red)
        assert isinstance(crossing.node, BraidingNode)
        assert crossing.node.left == red
        assert crossing.node.right == blue
    assert positive.node.sign is CrossingSign.POSITIVE
    assert negative.node.sign is CrossingSign.NEGATIVE
    assert positive != negative


def test_structural_cups_caps_and_twists_have_explicit_types() -> None:
    category = CategorySpec("structural")
    value = category.object("V")
    unit = category.unit

    cap_left = category.evaluation(value, dual_position=DualPosition.LEFT)
    cap_right = category.evaluation(value, dual_position=DualPosition.RIGHT)
    cup_left = category.coevaluation(value, dual_position=DualPosition.LEFT)
    cup_right = category.coevaluation(value, dual_position=DualPosition.RIGHT)
    inverse_twist = category.twist(value, inverse=True)

    assert cap_left.dom == value.dual.tensor(value)
    assert cap_left.cod == unit
    assert cap_right.dom == value.tensor(value.dual)
    assert isinstance(cap_left.node, EvaluationNode)
    assert cup_left.dom == unit
    assert cup_left.cod == value.dual.tensor(value)
    assert cup_right.cod == value.tensor(value.dual)
    assert isinstance(cup_left.node, CoevaluationNode)
    assert inverse_twist.dom == inverse_twist.cod == value
    assert isinstance(inverse_twist.node, TwistNode)
    assert inverse_twist.node.inverse


def test_cross_category_morphism_operations_and_factories_are_rejected() -> None:
    first = CategorySpec("first")
    second = CategorySpec("second")
    first_object = first.object("V")
    second_object = second.object("V")
    first_coupon = first.coupon("f", first_object, first_object)
    second_coupon = second.coupon("g", second_object, second_object)

    with pytest.raises(CategoryMismatchError, match="different categories"):
        first_coupon.then(second_coupon)
    with pytest.raises(CategoryMismatchError, match="different categories"):
        first_coupon.tensor(second_coupon)
    with pytest.raises(CategoryMismatchError, match="not 'first'"):
        first.coupon("foreign", first_object, second_object)
    with pytest.raises(CategoryMismatchError, match="not 'first'"):
        first.braiding(first_object, second_object)
