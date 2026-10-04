import epdlib


def test_version_is_v1():
    assert epdlib.__version__.startswith("1.")
