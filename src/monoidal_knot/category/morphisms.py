"""Immutable, typed morphism abstract syntax trees."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from monoidal_knot.category.objects import ObjectExpr
from monoidal_knot.errors import CategoryMismatchError, DefinitionError, MorphismTypeError


class CrossingSign(StrEnum):
    """Sign of a colored braid crossing read from top to bottom."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class DualPosition(StrEnum):
    """Position of the dual factor in an evaluation or coevaluation word."""

    LEFT = "dual-left"
    RIGHT = "dual-right"


@dataclass(frozen=True, slots=True)
class IdentityNode:
    """Identity structural node; its object is carried by ``Morphism``."""


@dataclass(frozen=True, slots=True)
class CouponNode:
    """A user-declared, uninterpreted coupon in a string diagram."""

    coupon_id: str

    def __post_init__(self) -> None:
        if not self.coupon_id or self.coupon_id.isspace():
            raise DefinitionError("A coupon identifier must be non-empty.")


@dataclass(frozen=True, slots=True)
class ComposeNode:
    """A flattened, top-to-bottom sequence of morphisms."""

    morphisms: tuple[Morphism, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.morphisms, tuple):
            raise DefinitionError("ComposeNode children must be stored as a tuple.")


@dataclass(frozen=True, slots=True)
class TensorNode:
    """A flattened, left-to-right tensor product of morphisms."""

    morphisms: tuple[Morphism, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.morphisms, tuple):
            raise DefinitionError("TensorNode children must be stored as a tuple.")


@dataclass(frozen=True, slots=True)
class BraidingNode:
    """A colored crossing whose arguments are the incoming top objects."""

    left: ObjectExpr
    right: ObjectExpr
    sign: CrossingSign


@dataclass(frozen=True, slots=True)
class EvaluationNode:
    """A cap for the chosen pivotal dual."""

    object: ObjectExpr
    dual_position: DualPosition


@dataclass(frozen=True, slots=True)
class CoevaluationNode:
    """A cup for the chosen pivotal dual."""

    object: ObjectExpr
    dual_position: DualPosition


@dataclass(frozen=True, slots=True)
class TwistNode:
    """A ribbon twist or its inverse."""

    object: ObjectExpr
    inverse: bool = False


type MorphismNode = (
    IdentityNode
    | CouponNode
    | ComposeNode
    | TensorNode
    | BraidingNode
    | EvaluationNode
    | CoevaluationNode
    | TwistNode
)


@dataclass(frozen=True, slots=True)
class Morphism:
    """A typed morphism with immutable syntax and syntactic equality."""

    dom: ObjectExpr
    cod: ObjectExpr
    node: MorphismNode

    def __post_init__(self) -> None:
        if self.dom.category_id != self.cod.category_id:
            raise CategoryMismatchError(
                "A morphism domain and codomain must belong to the same category."
            )
        _validate_node_type(self)

    @property
    def category_id(self) -> str:
        """The category determined by the morphism's type."""

        return self.dom.category_id

    @property
    def is_identity(self) -> bool:
        """Whether this is a syntactic identity node."""

        return isinstance(self.node, IdentityNode)

    def then(self, other: Morphism) -> Morphism:
        """Compose ``self`` first and ``other`` second, with eager type checking."""

        if self.category_id != other.category_id:
            raise CategoryMismatchError(
                "Cannot compose morphisms from different categories: "
                f"{self.category_id!r} and {other.category_id!r}."
            )
        if self.cod != other.dom:
            raise MorphismTypeError(
                "Cannot compose morphisms: the first codomain "
                f"{self.cod} does not equal the second domain {other.dom}."
            )
        if self.is_identity:
            return other
        if other.is_identity:
            return self

        parts: list[Morphism] = []
        for morphism in (self, other):
            if isinstance(morphism.node, ComposeNode):
                parts.extend(morphism.node.morphisms)
            else:
                parts.append(morphism)
        return type(self)(self.dom, other.cod, ComposeNode(tuple(parts)))

    def tensor(self, other: Morphism) -> Morphism:
        """Tensor morphisms left-to-right and flatten nested tensor nodes."""

        if self.category_id != other.category_id:
            raise CategoryMismatchError(
                "Cannot tensor morphisms from different categories: "
                f"{self.category_id!r} and {other.category_id!r}."
            )
        if self.is_identity and self.dom.is_unit:
            return other
        if other.is_identity and other.dom.is_unit:
            return self

        parts: list[Morphism] = []
        for morphism in (self, other):
            if isinstance(morphism.node, TensorNode):
                parts.extend(morphism.node.morphisms)
            else:
                parts.append(morphism)
        return type(self)(
            self.dom.tensor(other.dom),
            self.cod.tensor(other.cod),
            TensorNode(tuple(parts)),
        )

    def __str__(self) -> str:
        return f"{self.dom} -> {self.cod}"


def _validate_node_type(morphism: Morphism) -> None:
    """Reject manually assembled nodes whose payload conflicts with their type."""

    node = morphism.node
    if isinstance(node, IdentityNode):
        if morphism.dom != morphism.cod:
            raise MorphismTypeError("An identity morphism must have equal domain and codomain.")
        return
    if isinstance(node, CouponNode):
        return
    if isinstance(node, ComposeNode):
        if len(node.morphisms) < 2:
            raise DefinitionError("A ComposeNode must contain at least two morphisms.")
        if node.morphisms[0].dom != morphism.dom or node.morphisms[-1].cod != morphism.cod:
            raise MorphismTypeError("A ComposeNode payload does not match its declared outer type.")
        for first, second in zip(node.morphisms, node.morphisms[1:], strict=False):
            if first.cod != second.dom:
                raise MorphismTypeError("Adjacent ComposeNode morphisms are not composable.")
        if any(item.category_id != morphism.category_id for item in node.morphisms):
            raise CategoryMismatchError("Every ComposeNode child must use the outer category.")
        if any(item.is_identity or isinstance(item.node, ComposeNode) for item in node.morphisms):
            raise DefinitionError(
                "ComposeNode children must already be flattened and non-identity."
            )
        return
    if isinstance(node, TensorNode):
        if len(node.morphisms) < 2:
            raise DefinitionError("A TensorNode must contain at least two morphisms.")
        children = node.morphisms
        expected_dom = children[0].dom
        expected_cod = children[0].cod
        for item in children[1:]:
            expected_dom = expected_dom.tensor(item.dom)
            expected_cod = expected_cod.tensor(item.cod)
        if expected_dom != morphism.dom or expected_cod != morphism.cod:
            raise MorphismTypeError("A TensorNode payload does not match its declared outer type.")
        if any(isinstance(item.node, TensorNode) for item in children):
            raise DefinitionError("TensorNode children must already be flattened.")
        if any(item.is_identity and item.dom.is_unit for item in children):
            raise DefinitionError("TensorNode children must not contain the unit identity.")
        return
    if isinstance(node, BraidingNode):
        if not isinstance(node.sign, CrossingSign):
            raise DefinitionError("A braiding sign must be a CrossingSign value.")
        if node.left.tensor(node.right) != morphism.dom:
            raise MorphismTypeError("A braiding domain must be left tensor right.")
        if node.right.tensor(node.left) != morphism.cod:
            raise MorphismTypeError("A braiding codomain must be right tensor left.")
        return
    if isinstance(node, (EvaluationNode, CoevaluationNode)):
        if not isinstance(node.dual_position, DualPosition):
            raise DefinitionError("A dual position must be a DualPosition value.")
        unit = ObjectExpr(node.object.category_id)
        if node.dual_position is DualPosition.LEFT:
            paired = node.object.dual.tensor(node.object)
        else:
            paired = node.object.tensor(node.object.dual)
        expected = (paired, unit) if isinstance(node, EvaluationNode) else (unit, paired)
        if (morphism.dom, morphism.cod) != expected:
            raise MorphismTypeError("A cup or cap payload does not match its declared outer type.")
        return
    if isinstance(node, TwistNode):
        if not isinstance(node.inverse, bool):
            raise DefinitionError("TwistNode.inverse must be a boolean.")
        if morphism.dom != node.object or morphism.cod != node.object:
            raise MorphismTypeError("A twist must be an endomorphism of its payload object.")
        return
    raise DefinitionError(f"Unsupported morphism node type: {type(node).__name__}.")


def identity(object_expr: ObjectExpr) -> Morphism:
    """Construct an identity morphism."""

    return Morphism(object_expr, object_expr, IdentityNode())


def coupon(coupon_id: str, dom: ObjectExpr, cod: ObjectExpr) -> Morphism:
    """Construct an arbitrary typed coupon with no imposed relations."""

    return Morphism(dom, cod, CouponNode(coupon_id))


def braiding(
    left: ObjectExpr,
    right: ObjectExpr,
    *,
    sign: CrossingSign = CrossingSign.POSITIVE,
) -> Morphism:
    """Construct a colored crossing from ``left ⊗ right`` to ``right ⊗ left``.

    A positive crossing denotes ``c_(left,right)``.  A negative crossing with
    incoming objects ``left,right`` denotes ``c_(right,left)^-1`` so that both
    signs have the same displayed input and output types.
    """

    dom = left.tensor(right)
    cod = right.tensor(left)
    return Morphism(dom, cod, BraidingNode(left, right, sign))


def evaluation(object_expr: ObjectExpr, *, dual_position: DualPosition) -> Morphism:
    """Construct a typed cap for the selected pivotal dual."""

    unit = ObjectExpr(object_expr.category_id)
    if dual_position is DualPosition.LEFT:
        dom = object_expr.dual.tensor(object_expr)
    else:
        dom = object_expr.tensor(object_expr.dual)
    return Morphism(dom, unit, EvaluationNode(object_expr, dual_position))


def coevaluation(object_expr: ObjectExpr, *, dual_position: DualPosition) -> Morphism:
    """Construct a typed cup for the selected pivotal dual."""

    unit = ObjectExpr(object_expr.category_id)
    if dual_position is DualPosition.LEFT:
        cod = object_expr.dual.tensor(object_expr)
    else:
        cod = object_expr.tensor(object_expr.dual)
    return Morphism(unit, cod, CoevaluationNode(object_expr, dual_position))


def twist(object_expr: ObjectExpr, *, inverse: bool = False) -> Morphism:
    """Construct a ribbon twist structural node."""

    return Morphism(object_expr, object_expr, TwistNode(object_expr, inverse))
