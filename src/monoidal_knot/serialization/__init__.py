"""Versioned, human-readable JSON persistence for reproducible experiments."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sympy  # type: ignore[import-untyped]

from monoidal_knot.braid import BraidMorphism, FramedClosure
from monoidal_knot.category import (
    BraidingNode,
    CategorySpec,
    CoevaluationNode,
    ComposeNode,
    CouponNode,
    CrossingSign,
    DualPosition,
    EvaluationNode,
    IdentityNode,
    Morphism,
    ObjectExpr,
    ObjectFactor,
    TensorNode,
    TwistNode,
)
from monoidal_knot.errors import SerializationError
from monoidal_knot.functor import MarkovTraceParameters, QuantumTrace, RMatrixSpec
from monoidal_knot.symbolic import ExactMatrix, GrassmannAlgebra, ScalarExpr
from monoidal_knot.validation import ValidationReport

SCHEMA = "monoidal-knot"
SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    """Portable inputs and outputs needed to audit one closure experiment."""

    category: CategorySpec
    braid: BraidMorphism
    r_matrices: tuple[tuple[ObjectExpr, ObjectExpr, RMatrixSpec], ...]
    trace_data: QuantumTrace | None
    validation: ValidationReport
    raw_value: ScalarExpr | None = None
    normalized_value: ScalarExpr | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.braid.category_id != self.category.id:
            raise SerializationError("Experiment braid and category identifiers must agree.")


def to_data(value: object) -> dict[str, Any]:
    """Convert a supported value to a versioned JSON-compatible document."""

    return {"schema": SCHEMA, "version": SCHEMA_VERSION, "payload": _encode(value)}


def from_data(document: object) -> object:
    """Validate and decode a document produced by :func:`to_data`."""

    if not isinstance(document, dict):
        raise SerializationError("A serialized document must be a JSON object.")
    if document.get("schema") != SCHEMA:
        raise SerializationError(f"Unsupported serialization schema: {document.get('schema')!r}.")
    if document.get("version") != SCHEMA_VERSION:
        raise SerializationError(
            f"Unsupported {SCHEMA} schema version: {document.get('version')!r}."
        )
    try:
        return _Decoder().decode(document["payload"])
    except SerializationError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise SerializationError(f"Invalid serialized payload: {error}") from error


def dumps(value: object, *, indent: int | None = 2) -> str:
    """Serialize a supported value as deterministic UTF-8 JSON text."""

    return json.dumps(to_data(value), ensure_ascii=False, indent=indent, sort_keys=True)


def loads(text: str) -> object:
    """Deserialize JSON text, rejecting malformed documents consistently."""

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise SerializationError(f"Invalid JSON: {error.msg}.") from error
    return from_data(document)


def save(value: object, path: str | Path) -> None:
    """Atomically save a supported value to a UTF-8 JSON file."""

    target = Path(path)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(dumps(value) + "\n", encoding="utf-8")
    temporary.replace(target)


def load(path: str | Path) -> object:
    """Load one UTF-8 JSON document."""

    return loads(Path(path).read_text(encoding="utf-8"))


def _encode(value: object) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, CategorySpec):
        return {"type": "category", "id": value.id, "name": value.name}
    if isinstance(value, ObjectFactor):
        return {"generator": value.generator_id, "dual": value.is_dual}
    if isinstance(value, ObjectExpr):
        return {
            "type": "object",
            "category": value.category_id,
            "factors": [_encode(x) for x in value.factors],
        }
    if isinstance(value, Morphism):
        return {
            "type": "morphism",
            "dom": _encode(value.dom),
            "cod": _encode(value.cod),
            "node": _encode_node(value.node),
        }
    if isinstance(value, BraidMorphism):
        return {"type": "braid", "objects": _encode(value.objects), "word": list(value.word)}
    if isinstance(value, FramedClosure):
        return {"type": "closure", "braid": _encode(value.braid)}
    if isinstance(value, GrassmannAlgebra):
        return {
            "type": "grassmann-algebra",
            "id": value.id,
            "generators": list(value.generator_names),
        }
    if isinstance(value, ScalarExpr):
        algebra = value.algebra
        return {
            "type": "scalar",
            "algebra": _encode(algebra) if algebra is not None else None,
            "terms": [
                {
                    "mask": 0 if monomial is None else monomial.mask,
                    "coefficient": sympy.srepr(coefficient),
                }
                for monomial, coefficient in value.terms
            ],
        }
    if isinstance(value, ExactMatrix):
        return {"type": "matrix", "rows": [[_encode(x) for x in row] for row in value.rows]}
    if isinstance(value, RMatrixSpec):
        return {
            "type": "r-matrix",
            "convention": value.convention.value,
            "matrix": _encode(value.matrix),
        }
    if isinstance(value, MarkovTraceParameters):
        return {
            "type": "markov-parameters",
            "alpha": _encode(value.alpha),
            "beta": _encode(value.beta),
            "overall_scale": _encode(value.overall_scale),
        }
    if isinstance(value, QuantumTrace):
        return {
            "type": "quantum-trace",
            "weights": [
                {"object": _encode(k), "matrix": _encode(v)} for k, v in value.weights.items()
            ],
            "parameters": _encode(value.parameters),
        }
    if isinstance(value, ValidationReport):
        return {
            "type": "validation-report",
            "status": value.status.value,
            "verified": value.verified,
            "checks": [
                {
                    "key": c.key,
                    "status": c.status.value,
                    "summary": c.summary,
                    "required": c.required,
                    "evidence": str(c.evidence) if c.evidence is not None else None,
                }
                for c in value.checks
            ],
        }
    if isinstance(value, ExperimentRecord):
        return {
            "type": "experiment",
            "category": _encode(value.category),
            "braid": _encode(value.braid),
            "r_matrices": [
                {"left": _encode(a), "right": _encode(b), "spec": _encode(s)}
                for a, b, s in value.r_matrices
            ],
            "trace_data": _encode(value.trace_data),
            "validation": _encode(value.validation),
            "raw_value": _encode(value.raw_value),
            "normalized_value": _encode(value.normalized_value),
            "metadata": dict(value.metadata),
        }
    raise SerializationError(f"Unsupported value for serialization: {type(value).__name__}.")


def _encode_node(node: object) -> dict[str, Any]:
    if isinstance(node, IdentityNode):
        return {"kind": "identity"}
    if isinstance(node, CouponNode):
        return {"kind": "coupon", "id": node.coupon_id}
    if isinstance(node, ComposeNode):
        return {"kind": "compose", "morphisms": [_encode(x) for x in node.morphisms]}
    if isinstance(node, TensorNode):
        return {"kind": "tensor", "morphisms": [_encode(x) for x in node.morphisms]}
    if isinstance(node, BraidingNode):
        return {
            "kind": "braiding",
            "left": _encode(node.left),
            "right": _encode(node.right),
            "sign": node.sign.value,
        }
    if isinstance(node, EvaluationNode):
        return {
            "kind": "evaluation",
            "object": _encode(node.object),
            "dual_position": node.dual_position.value,
        }
    if isinstance(node, CoevaluationNode):
        return {
            "kind": "coevaluation",
            "object": _encode(node.object),
            "dual_position": node.dual_position.value,
        }
    if isinstance(node, TwistNode):
        return {"kind": "twist", "object": _encode(node.object), "inverse": node.inverse}
    raise SerializationError(f"Unsupported morphism node: {type(node).__name__}.")


class _Decoder:
    def __init__(self) -> None:
        self.algebras: dict[tuple[str, tuple[str, ...]], GrassmannAlgebra] = {}

    def decode(self, data: Any) -> Any:
        if data is None or isinstance(data, (bool, int, str)):
            return data
        if not isinstance(data, dict) or not isinstance(data.get("type"), str):
            raise SerializationError("Every encoded value must have a string type tag.")
        kind = data["type"]
        if kind == "category":
            return CategorySpec(data["id"], data["name"])
        if kind == "object":
            return ObjectExpr(
                data["category"],
                tuple(ObjectFactor(x["generator"], x["dual"]) for x in data["factors"]),
            )
        if kind == "braid":
            return BraidMorphism(self.decode(data["objects"]), tuple(data["word"]))
        if kind == "closure":
            return FramedClosure(self.decode(data["braid"]))
        if kind == "morphism":
            dom, cod = self.decode(data["dom"]), self.decode(data["cod"])
            return Morphism(dom, cod, self._node(data["node"]))
        if kind == "grassmann-algebra":
            return self._algebra(data)
        if kind == "scalar":
            return self._scalar(data)
        if kind == "matrix":
            return ExactMatrix([[self.decode(x) for x in row] for row in data["rows"]])
        if kind == "r-matrix":
            return RMatrixSpec(self.decode(data["matrix"]), convention=data["convention"])
        if kind == "markov-parameters":
            return MarkovTraceParameters(
                alpha=self.decode(data["alpha"]),
                beta=self.decode(data["beta"]),
                overall_scale=self.decode(data["overall_scale"]),
            )
        if kind == "quantum-trace":
            weights = {self.decode(x["object"]): self.decode(x["matrix"]) for x in data["weights"]}
            return QuantumTrace(weights, parameters=self.decode(data["parameters"]))
        if kind == "validation-report":
            from monoidal_knot.validation import CheckStatus, ValidationCheck

            return ValidationReport.from_checks(
                ValidationCheck(
                    x["key"], CheckStatus(x["status"]), x["summary"], x["required"], x["evidence"]
                )
                for x in data["checks"]
            )
        if kind == "experiment":
            return ExperimentRecord(
                category=self.decode(data["category"]),
                braid=self.decode(data["braid"]),
                r_matrices=tuple(
                    (self.decode(x["left"]), self.decode(x["right"]), self.decode(x["spec"]))
                    for x in data["r_matrices"]
                ),
                trace_data=self.decode(data["trace_data"]),
                validation=self.decode(data["validation"]),
                raw_value=self.decode(data["raw_value"]),
                normalized_value=self.decode(data["normalized_value"]),
                metadata=dict(data["metadata"]),
            )
        raise SerializationError(f"Unknown serialized type tag: {kind!r}.")

    def _algebra(self, data: dict[str, Any]) -> GrassmannAlgebra:
        key = (data["id"], tuple(data["generators"]))
        if key not in self.algebras:
            algebra = GrassmannAlgebra(key[0])
            algebra.symbols(*key[1])
            self.algebras[key] = algebra
        return self.algebras[key]

    def _scalar(self, data: dict[str, Any]) -> ScalarExpr:
        algebra = None if data["algebra"] is None else self.decode(data["algebra"])
        result = ScalarExpr()
        for term in data["terms"]:
            coefficient = ScalarExpr(sympy.sympify(term["coefficient"], evaluate=False))
            mask = term["mask"]
            if mask:
                assert isinstance(algebra, GrassmannAlgebra)
                for index, name in enumerate(algebra.generator_names):
                    if mask & (1 << index):
                        coefficient *= algebra.symbol(name)
            result += coefficient
        return result

    def _node(self, data: dict[str, Any]) -> Any:
        kind = data["kind"]
        if kind == "identity":
            return IdentityNode()
        if kind == "coupon":
            return CouponNode(data["id"])
        if kind == "compose":
            return ComposeNode(tuple(self.decode(x) for x in data["morphisms"]))
        if kind == "tensor":
            return TensorNode(tuple(self.decode(x) for x in data["morphisms"]))
        if kind == "braiding":
            return BraidingNode(
                self.decode(data["left"]), self.decode(data["right"]), CrossingSign(data["sign"])
            )
        if kind == "evaluation":
            return EvaluationNode(self.decode(data["object"]), DualPosition(data["dual_position"]))
        if kind == "coevaluation":
            return CoevaluationNode(
                self.decode(data["object"]), DualPosition(data["dual_position"])
            )
        if kind == "twist":
            return TwistNode(self.decode(data["object"]), data["inverse"])
        raise SerializationError(f"Unknown morphism node kind: {kind!r}.")


__all__ = [
    "SCHEMA",
    "SCHEMA_VERSION",
    "ExperimentRecord",
    "dumps",
    "from_data",
    "load",
    "loads",
    "save",
    "to_data",
]
