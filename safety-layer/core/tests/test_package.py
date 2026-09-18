from importlib.resources import files

import safety_layer


def test_package_ships_type_information() -> None:
    # Without py.typed, mypy treats every consumer's import of the engine as untyped.
    assert files(safety_layer).joinpath("py.typed").is_file()
