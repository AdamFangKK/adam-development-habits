def fib_mod(n, modulus):
    if n <= 1:
        return 1
    return (fib_mod(n - 1, modulus) + fib_mod(n - 2, modulus)) % modulus
