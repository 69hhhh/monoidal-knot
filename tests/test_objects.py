import pytest

from monoidal_knot import CategoryMismatchError, CategorySpec, DefinitionError


def test_unit_and_tensor_words_are_canonical_and_associative() -> None:
    category = CategorySpec("colored")
    unit = category.unit
    red = category.object("red")
    green = category.object("green")
    blue = category.object("blue")

    assert unit.tensor(red) == red
    assert red.tensor(unit) == red
    assert red.tensor(green).tensor(blue) == red.tensor(green.tensor(blue))
    assert red.tensor(green).factors == red.factors + green.factors


def test_dual_reverses_tensor_words_and_is_strictly_involutive() -> None:
    category = CategorySpec("dual")
    left = category.object("A")
    right = category.object("B")

    assert left.dual.dual == left
    assert left.tensor(right).dual == right.dual.tensor(left.dual)
    assert category.unit.dual == category.unit


def test_object_expressions_are_hashable() -> None:
    category = CategorySpec("hash")
    first = category.object("A").tensor(category.object("B"))
    second = category.object("A").tensor(category.object("B"))

    assert first == second
    assert {first, second} == {first}


def test_tensor_power_includes_zero_and_rejects_negative_exponents() -> None:
    category = CategorySpec("powers")
    value = category.object("V")

    assert value.tensor_power(0) == category.unit
    assert value.tensor_power(3).factors == value.factors * 3
    with pytest.raises(DefinitionError, match="nonnegative"):
        value.tensor_power(-1)


def test_cross_category_tensor_is_rejected() -> None:
    left = CategorySpec("left").object("V")
    right = CategorySpec("right").object("V")

    with pytest.raises(CategoryMismatchError, match="different categories"):
        left.tensor(right)


@pytest.mark.parametrize("identifier", ["", "   "])
def test_blank_category_and_object_identifiers_are_rejected(identifier: str) -> None:
    with pytest.raises(DefinitionError, match="category identifier"):
        CategorySpec(identifier)

    category = CategorySpec("valid")
    with pytest.raises(DefinitionError, match="generating object"):
        category.object(identifier)
