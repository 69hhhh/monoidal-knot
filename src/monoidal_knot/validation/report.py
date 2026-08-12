"""Four-state validation reports that never confuse unknown with success."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from monoidal_knot.errors import ValidationError


class CheckStatus(StrEnum):
    """Outcome of an exact validation check."""

    PASSED = "passed"
    FAILED = "failed"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    """One named condition and optional exact evidence such as a residual."""

    key: str
    status: CheckStatus
    summary: str
    required: bool = True
    evidence: object | None = None

    def __post_init__(self) -> None:
        if not self.key or self.key.isspace():
            raise ValidationError("A validation check key must be non-empty.")
        if not self.summary or self.summary.isspace():
            raise ValidationError("A validation check summary must be non-empty.")


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Immutable aggregate whose verified state requires all required checks to pass."""

    checks: tuple[ValidationCheck, ...] = ()

    def __post_init__(self) -> None:
        keys = tuple(check.key for check in self.checks)
        if len(keys) != len(set(keys)):
            raise ValidationError("Validation check keys must be unique within a report.")

    @classmethod
    def from_checks(cls, checks: Iterable[ValidationCheck]) -> Self:
        """Build a report from any finite iterable of checks."""

        return cls(tuple(checks))

    @property
    def status(self) -> CheckStatus:
        """Aggregate required checks, with failure taking precedence over uncertainty."""

        required = tuple(check for check in self.checks if check.required)
        if any(check.status is CheckStatus.FAILED for check in required):
            return CheckStatus.FAILED
        if not required or any(
            check.status in {CheckStatus.UNKNOWN, CheckStatus.SKIPPED} for check in required
        ):
            return CheckStatus.UNKNOWN
        return CheckStatus.PASSED

    @property
    def verified(self) -> bool:
        """Return true only when every required condition was actually checked and passed."""

        return self.status is CheckStatus.PASSED

    @property
    def failures(self) -> tuple[ValidationCheck, ...]:
        """Return all failed checks, including optional diagnostics."""

        return tuple(check for check in self.checks if check.status is CheckStatus.FAILED)

    @property
    def inconclusive(self) -> tuple[ValidationCheck, ...]:
        """Return checks that were unknown or skipped."""

        return tuple(
            check
            for check in self.checks
            if check.status in {CheckStatus.UNKNOWN, CheckStatus.SKIPPED}
        )

    def __bool__(self) -> bool:
        """Reject ambiguous truth testing; callers must inspect status or verified."""

        raise TypeError("ValidationReport has no implicit truth value; use .verified or .status.")
