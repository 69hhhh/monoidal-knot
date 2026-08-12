import monoidal_knot


def test_package_imports_with_pre_alpha_version() -> None:
    assert monoidal_knot.__version__ == "0.0.1"
