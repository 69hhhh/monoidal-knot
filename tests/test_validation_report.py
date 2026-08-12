import pytest

from monoidal_knot import CheckStatus, ValidationCheck, ValidationError, ValidationReport


def check(key: str, status: CheckStatus, *, required: bool = True) -> ValidationCheck:
    return ValidationCheck(key, status, f"{key} is {status.value}", required=required)


def test_empty_report_is_unknown_not_verified() -> None:
    report = ValidationReport()

    assert report.status is CheckStatus.UNKNOWN
    assert not report.verified


def test_all_required_checks_must_pass_for_verification() -> None:
    report = ValidationReport.from_checks(
        [
            check("shape", CheckStatus.PASSED),
            check("yang-baxter", CheckStatus.PASSED),
            check("optional-note", CheckStatus.UNKNOWN, required=False),
        ]
    )

    assert report.status is CheckStatus.PASSED
    assert report.verified
    assert tuple(item.key for item in report.inconclusive) == ("optional-note",)


def test_failure_takes_precedence_over_unknown() -> None:
    residual = ((0, 1), (0, 0))
    report = ValidationReport.from_checks(
        [
            check("symbolic-zero", CheckStatus.UNKNOWN),
            ValidationCheck(
                "yang-baxter",
                CheckStatus.FAILED,
                "Yang-Baxter residual is nonzero",
                evidence=residual,
            ),
        ]
    )

    assert report.status is CheckStatus.FAILED
    assert not report.verified
    assert report.failures[0].evidence == residual


def test_required_skipped_check_is_unknown() -> None:
    report = ValidationReport((check("trace", CheckStatus.SKIPPED),))

    assert report.status is CheckStatus.UNKNOWN
    assert not report.verified


def test_report_rejects_implicit_truth_testing() -> None:
    with pytest.raises(TypeError, match="no implicit truth value"):
        bool(ValidationReport())


def test_report_rejects_duplicate_keys() -> None:
    with pytest.raises(ValidationError, match="unique"):
        ValidationReport(
            (
                check("shape", CheckStatus.PASSED),
                check("shape", CheckStatus.FAILED),
            )
        )
