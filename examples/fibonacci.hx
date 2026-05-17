# Fibonacci — iterative and recursive, with verification

@verify(pre="n >= 0", post="result >= 0")
fn fib_recursive(n):
    if n <= 1:
        return n
    return fib_recursive(n - 1) + fib_recursive(n - 2)


fn fib_iterative(n):
    if n <= 1:
        return n
    let a = 0
    let b = 1
    for _ in range(n - 1):
        let tmp = a + b
        a = b
        b = tmp
    return b


fn fib_sequence(count):
    let result = []
    for i in range(count):
        result += [fib_iterative(i)]
    return result


# Memoized version using a closure
fn make_fib_memo():
    let cache = {}
    fn fib(n):
        if n in cache:
            return cache[n]
        if n <= 1:
            cache[n] = n
            return n
        let val = fib(n - 1) + fib(n - 2)
        cache[n] = val
        return val
    return fib


let fib = make_fib_memo()
let seq = [fib(i) for i in range(15)]
print("Fibonacci (memoized):", seq)

# Verify recursive matches iterative
for i in range(10):
    let r = fib_recursive(i)
    let it = fib_iterative(i)
    assert r == it, f"Mismatch at n={i}: recursive={r}, iterative={it}"

print("All assertions passed!")
