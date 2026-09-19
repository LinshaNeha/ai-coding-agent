def add_numbers(a, b):
    """Should return the sum of a and b."""
    return a + b


def average(numbers):
    """Should return the average of a list of numbers."""
    if not numbers:
        return 0
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)


def is_prime(n):
    """Should return True if n is a prime number, False otherwise."""
    if n < 2:
        return False
    for i in range(2, n):
        if n % i == 0:
            return False
    return True


def factorial(n):
    """Should return n! (n factorial)."""
    if n < 0:
        raise ValueError("factorial not defined for negative numbers")
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result