import pytest
from routers.auth import validate_password_strength


@pytest.mark.parametrize(
    "password, should_pass",
    [
        ("short1!", False),  # too short
        ("lowercase123!", False),  # no uppercase
        ("NoSymbolHere1", False),  # no symbol
        ("ValidPass1!", True),
        ("Another$Good9", True),
    ],
)
def test_password_strength(password, should_pass):
    if should_pass:
        assert validate_password_strength(password) == password
    else:
        with pytest.raises(ValueError):
            validate_password_strength(password)
