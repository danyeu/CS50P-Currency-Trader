import pytest
from fx import fx_received, base_received, str_to_tuple2dp, tuple2dp_greaterthan, tuple2dp_add


def test_fx_received():
    assert fx_received((9999, 9999), (0, 0)) == (0, 0)
    assert fx_received((1, 0), (1, 0)) == (1, 0)
    assert fx_received((9999, 9900), (1, 0)) == (9999, 99)
    assert fx_received((9999, 9999), (1, 0)) == (9999, 99)
    assert fx_received((9999, 9900), (9999, 99)) == (99999800, 0)
    assert fx_received((9999, 9999), (9999, 99)) == (99999899, 0)
    assert fx_received((125, 5), (100, 50)) == (12562, 55)
    assert fx_received((0, 1), (99, 99)) == (0, 0)
    assert fx_received((0, 1234), (56, 78)) == (7, 0)
    assert fx_received((1, 35), (2500, 0)) == (2508, 75)
    assert fx_received((0, 789), (10, 11)) == (0, 79)
    assert fx_received((44, 9732), (3210, 1)) == (144364, 42)
    assert fx_received((7, 8497), (10, 25)) == (80, 45)
    with pytest.raises(TypeError):
        fx_received(125.0005, 100.5)
        fx_received((125, 5), 100.5)
        fx_received(125.0005, (100, 50))
        fx_received(125, 100.5)
        fx_received((125, 5), 100)
        fx_received(125, (100, 50))
        fx_received("12.0005", 100.5)
        fx_received(12.0005, "100.5")
        fx_received("12.0005", "100.5")
        fx_received("(12,5)", (100, 50))
        fx_received((12, 5), "(100,50)")
        fx_received("(12, 5)", "(100,50)")
    with pytest.raises(ValueError):
        fx_received((1, 1, 1), (1, 1))
        fx_received((1, 1), (1, 1, 1))
        fx_received((1, 1, 1), (1, 1, 1))
        fx_received((125, 5), (0, 10050))
        fx_received((0, 1250005), (100, 50))
        fx_received((-1, 0), (1, 0))
        fx_received((1, 0), (-1, 0))
        fx_received((1, -1), (1, 0))
        fx_received((1, 0), (1, -1))
        fx_received((0, 0), (1, 0))


def test_base_received():
    assert base_received((9999, 9999), (0, 0)) == (0, 0)
    assert base_received((1, 0), (1, 0)) == (1, 0)
    assert base_received((9999, 9900), (1, 0)) == (0, 0)
    assert base_received((9999, 9999), (1, 0)) == (0, 0)
    assert base_received((9999, 9900), (9999, 99)) == (1, 0)
    assert base_received((9999, 9999), (9999, 99)) == (0, 99)
    assert base_received((125, 5), (100, 50)) == (0, 80)
    assert base_received((0, 1), (99, 99)) == (999900, 0)
    assert base_received((0, 1234), (56, 78)) == (460, 12)
    assert base_received((1, 35), (2500, 0)) == (2491, 28)
    assert base_received((0, 789), (10, 11)) == (128, 13)
    assert base_received((44, 9732), (3210, 1)) == (71, 37)
    assert base_received((7, 8497), (10, 25)) == (1, 30)
    with pytest.raises(TypeError):
        base_received(125.0005, 100.5)
        base_received((125, 5), 100.5)
        base_received(125.0005, (100, 50))
        base_received(125, 100.5)
        base_received((125, 5), 100)
        base_received(125, (100, 50))
        base_received("12.0005", 100.5)
        base_received(12.0005, "100.5")
        base_received("12.0005", "100.5")
        base_received("(12,5)", (100, 50))
        base_received((12, 5), "(100,50)")
        base_received("(12, 5)", "(100,50)")
    with pytest.raises(ValueError):
        base_received((1, 1, 1), (1, 1))
        base_received((1, 1), (1, 1, 1))
        base_received((1, 1, 1), (1, 1, 1))
        base_received((125, 5), (0, 10050))
        base_received((0, 1250005), (100, 50))
        base_received((-1, 0), (1, 0))
        base_received((1, 0), (-1, 0))
        base_received((1, -1), (1, 0))
        base_received((1, 0), (1, -1))
        base_received((0, 0), (1, 0))


def test_str_to_tuple2dp():
    # valid
    # leading zeroes ok
    for a in ["0" * i + "1" for i in range(10)]:
        # int + trailing "." ok
        assert str_to_tuple2dp(a + ".") == (1, 0)
        # trailing zeroes after "." ok
        for b in [".0" + "0" * i for i in range(10)]:
            assert str_to_tuple2dp(a) == (1, 0)
            assert str_to_tuple2dp(b) == (0, 0)
            assert str_to_tuple2dp(a + b) == (1, 0)
        # precision up to 2dps ok
        for c in [".01" + "0" * i for i in range(10)]:
            assert str_to_tuple2dp(c) == (0, 1)
            assert str_to_tuple2dp(a + c) == (1, 1)
    # invalid
    with pytest.raises(ValueError):
        # non-numeric
        str_to_tuple2dp("")
        str_to_tuple2dp(" ")
        str_to_tuple2dp(".")
        str_to_tuple2dp("abc")
        str_to_tuple2dp("..1")
        str_to_tuple2dp(".1.")
        str_to_tuple2dp("1..")
        str_to_tuple2dp("0.1.0")
        str_to_tuple2dp("1..0")
        str_to_tuple2dp("1-1")
        str_to_tuple2dp("1.-1")
        # too precise
        str_to_tuple2dp("3.333")
        str_to_tuple2dp("4.4444")
        str_to_tuple2dp("5.55555")
        str_to_tuple2dp("1.001")
        str_to_tuple2dp("1.0001")
        str_to_tuple2dp("1.00001")
        # negative
        str_to_tuple2dp("-1")
        str_to_tuple2dp("-1.")
        str_to_tuple2dp("-.1")
        str_to_tuple2dp("-.01")
        str_to_tuple2dp("-1.1")
        str_to_tuple2dp("-11.11")


def test_tuple2dp_greaterthan():
    # a > b
    assert tuple2dp_greaterthan((1, 1), (1, 0))
    assert tuple2dp_greaterthan((2, 2), (1, 1))
    assert tuple2dp_greaterthan((22, 22), (11, 11))
    # a < b
    assert not tuple2dp_greaterthan((1, 0), (1, 1))
    assert not tuple2dp_greaterthan((1, 1), (2, 2))
    assert not tuple2dp_greaterthan((11, 11), (22, 22))
    # a = b
    assert not tuple2dp_greaterthan((1, 0), (1, 0))
    assert not tuple2dp_greaterthan((22, 22), (22, 22))


def test_tuple2dp_add():
    # both positive
    assert tuple2dp_add((1, 2), (3, 4)) == (4, 6)
    assert tuple2dp_add((11, 22), (33, 44)) == (44, 66)
    assert tuple2dp_add((0, 99), (0, 1)) == (1, 0)
    assert tuple2dp_add((0, 1), (0, 99)) == (1, 0)
    assert tuple2dp_add((99, 99), (99, 99)) == (199, 98)
    # both negative (never used)
    assert tuple2dp_add((-1, -2), (-3, -4)) == (-4, -6)  # -1.02 - 3.04 = -4.06
    assert tuple2dp_add((-11, -22), (-33, -44)) == (-44, -66)  # -11.22 - 33.44 = -44.66
    assert tuple2dp_add((0, -99), (0, -1)) == (-1, 0)
    assert tuple2dp_add((0, -1), (0, -99)) == (-1, 0)
    assert tuple2dp_add((-99, -99), (-99, -99)) == (-199, -98)
    # one positive one negative = positive
    assert tuple2dp_add((-1, -2), (3, 4)) == (2, 2)
    assert tuple2dp_add((-11, -22), (33, 44)) == (22, 22)
    assert tuple2dp_add((1, 0), (0, -1)) == (0, 99)
    assert tuple2dp_add((0, -1), (1, 0)) == (0, 99)
    assert tuple2dp_add((99, 99), (-99, -99)) == (0, 0)
    assert tuple2dp_add((11, 11), (0, -99)) == (10, 12)
    # one positive one negative = negative
    assert tuple2dp_add((1, 2), (-3, -4)) == (-2, -2)
    assert tuple2dp_add((11, 22), (-33, -44)) == (-22, -22)
    assert tuple2dp_add((-1, 0), (0, 1)) == (0, -99)
    assert tuple2dp_add((0, 1), (-1, 0)) == (0, -99)
    assert tuple2dp_add((-99, -99), (99, 99)) == (0, 0)
    assert tuple2dp_add((-11, -11), (0, 99)) == (-10, -12)
    # invalid tuples
    with pytest.raises(ValueError):
        tuple2dp_add((-1, 1), (1, 1))
        tuple2dp_add((1, 1), (-1, 1))
        tuple2dp_add((1, -1), (1, 1))
        tuple2dp_add((1, 1), (1, -1))
        tuple2dp_add((-1, 1), (-1, 1))
        tuple2dp_add((1, -1), (1, -1))
        tuple2dp_add((-1, 1), (1, -1))
        tuple2dp_add((1, -1), (-1, 1))
