import pytest

from lety.ciselniky import _telefon


@pytest.mark.parametrize(
    ("vstup", "vysledek"),
    [
        (None, ""),
        ("", ""),
        ("731 123 456", "+420731123456"),
        (731123456, "+420731123456"),
        (731123456.0, "+420731123456"),
        ("+420 731 123 456", "+420731123456"),
        ("00421 905 123 456", "+421905123456"),
    ],
)
def test_telefon_do_mezinarodniho_tvaru(vstup, vysledek):
    assert _telefon(vstup) == vysledek
