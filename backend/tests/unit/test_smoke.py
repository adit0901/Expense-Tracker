def test_package_importable() -> None:
    import app

    assert app is not None
