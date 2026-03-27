import patience


def test_package_version_is_string() -> None:
    assert isinstance(patience.__version__, str)
    assert patience.__version__
