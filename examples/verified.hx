# Formal verification examples in Haxor
# Run with: haxor run examples/verified.hx --verify

# ── Pre/Post conditions ───────────────────────────────────────────────────────

@verify(pre="x >= 0", post="result >= 0")
fn integer_sqrt(x):
    """Integer square root — verified correct for non-negative input."""
    if x < 0:
        return -1  # should never happen due to precondition
    let lo = 0
    let hi = x
    while lo <= hi:
        let mid = (lo + hi) // 2
        if mid * mid == x:
            return mid
        elif mid * mid < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return hi


@verify(pre="n > 0", post="result > 0")
fn factorial(n):
    if n == 1:
        return 1
    return n * factorial(n - 1)


@verify(pre="len(lst) > 0")
fn safe_head(lst):
    """Get first element — precondition ensures list is non-empty."""
    return lst[0]


@verify(pre="high >= low", post="low <= result and result <= high")
fn clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


# ── Run examples ──────────────────────────────────────────────────────────────

print("=== Formal Verification Examples ===\n")

print("Integer square roots (verified >= 0):")
for n in [0, 1, 4, 9, 16, 25, 100]:
    let r = integer_sqrt(n)
    print(f"  isqrt({n}) = {r}")

print("\nFactorials (verified > 0):")
for n in range(1, 8):
    print(f"  {n}! = {factorial(n)}")

print("\nClamp examples (verified in range):")
for v in [-5, 0, 3, 7, 12]:
    let c = clamp(v, 0, 10)
    print(f"  clamp({v}, 0, 10) = {c}")

print("\nSafe head:")
let result = safe_head([10, 20, 30])
print(f"  head([10,20,30]) = {result}")

# This would raise VerificationError at runtime:
# safe_head([])

print("\nAll verifications passed!")


# ── Static analysis demo ──────────────────────────────────────────────────────
# Run: haxor verify examples/verified.hx
# The verifier will catch type mismatches and missing returns statically.

fn well_typed(x: int, y: int) -> int:
    return x + y

fn maybe_missing_return(x) -> int:
    if x > 0:
        return x
    # Missing return for x <= 0 — verifier will warn
