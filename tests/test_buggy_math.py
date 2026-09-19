from app.services.buggy_math import add_numbers, average, is_prime, factorial


def test_add_numbers():
    assert add_numbers(2, 3) == 5


def test_average():
    assert average([1, 2, 3, 4]) == 2.5


def test_average_empty():
    assert average([]) == 0


def test_is_prime_true():
    assert is_prime(7) is True


def test_is_prime_false():
    assert is_prime(8) is False


def test_factorial():
    assert factorial(5) == 120


def test_factorial_zero():
    assert factorial(0) == 1