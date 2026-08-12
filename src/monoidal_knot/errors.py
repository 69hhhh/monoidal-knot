"""Public exception hierarchy for monoidal-knot."""


class MonoidalKnotError(Exception):
    """Base class for package-specific errors."""


class DefinitionError(MonoidalKnotError):
    """A category, object, morphism, or model definition is invalid."""


class ConventionError(DefinitionError):
    """Input conflicts with a declared mathematical convention."""


class CategoryMismatchError(DefinitionError):
    """Objects or morphisms from different categories were combined."""


class MorphismTypeError(DefinitionError):
    """Domains or codomains make a morphism operation ill-typed."""


class EvaluationError(MonoidalKnotError):
    """An exact evaluation could not be completed."""


class SymbolicError(MonoidalKnotError):
    """A symbolic scalar operation is invalid or unsupported."""


class ScalarDomainError(SymbolicError):
    """Symbolic scalars from incompatible Grassmann algebras were combined."""


class NonInvertibleError(SymbolicError):
    """A symbolic scalar has no inverse in the implemented coefficient domain."""


class ExactMatrixError(MonoidalKnotError):
    """An exact matrix is malformed or an operation has incompatible shapes."""


class ValidationError(MonoidalKnotError):
    """A validation request or report is malformed."""


class SerializationError(MonoidalKnotError):
    """Versioned data could not be serialized or restored safely."""


class UnsupportedFeatureError(MonoidalKnotError):
    """The requested mathematical feature is outside the implemented scope."""
