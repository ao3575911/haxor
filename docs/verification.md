# Haxor Formal Verification

Haxor ships with a built-in static analyser and a runtime contract system.
Neither requires external tools — Z3 is supported optionally for stronger SMT-based
checking when installed (`pip install z3-solver`).

---

## Static verifier

Run the static verifier with:

```bash
haxor verify myfile.hx
haxor run myfile.hx --verify   # verify then execute
```

Three passes run in sequence:

### Pass 1 — Type inference

Performs monomorphic type inference over the AST.  Reports:
- **WARNING**: annotation mismatch (e.g. `let x: int = "hello"`)
- **WARNING**: possibly-undefined variable reference

### Pass 2 — Sign analysis

Abstract interpretation over the sign domain:
`{Bot, Neg, Zero, Pos, NonNeg, NonPos, NonZero, Top}`

Reports:
- **ERROR**: definite division by zero (e.g. `x / 0` where `0` is a known zero)

The analysis is *sound*: it only reports errors when division by zero is
*certain*, never when the divisor could be non-zero.

### Pass 3 — Control-flow analysis

Constructs a control-flow graph over each function body.  Reports:
- **WARNING**: function with non-None return type that may not return on all paths

---

## Runtime contracts (`@verify`)

The `@verify` decorator adds pre- and post-conditions that are checked at every
call site at runtime:

```haxor
@verify(pre="x >= 0 and x <= 1", post="result >= 0 and result <= 1")
fn lerp(a, b, x):
    return a + (b - a) * x
```

### Precondition (`pre`)

Evaluated with the function's parameters bound as variables.
If the expression evaluates to `False`, a `VerificationError` is raised
**before** the function body executes.

### Postcondition (`post`)

Evaluated after the function returns.  The return value is bound as `result`.
If the expression evaluates to `False`, a `VerificationError` is raised.

```haxor
@verify(pre="n > 0", post="result > 0 and result >= n")
fn cumulative_sum(n):
    let total = 0
    for i in range(1, n + 1):
        total += i
    return total
```

### Error messages

```
VerificationError [line 3:1]: Precondition failed for 'sqrt_approx': x > 0
VerificationError [line 3:1]: Postcondition failed for 'lerp': result >= 0 and result <= 1
```

---

## Z3 integration

If `z3-solver` is installed, the verifier can use SMT-based constraint solving
for stronger pre/post condition analysis:

```bash
pip install z3-solver
```

The verifier auto-detects Z3 and uses it in the `check_pre_post_z3` method.
Future versions will integrate Z3 more deeply for full symbolic verification.

---

## Diagnostics

All verifier output is structured as `Diagnostic` objects:

```python
from haxor.verifier import Verifier, Severity

tree = haxor.parse(source)
diags = Verifier().verify(tree)

for d in diags:
    print(d.severity.name, d.message, d.line, d.col, d.pass_name)
```

Severity levels: `INFO`, `WARNING`, `ERROR`.

Strict mode raises `VerificationError` on any ERROR diagnostic:

```python
Verifier(strict=True).verify(tree)
```

---

## Design philosophy

Haxor's verification is designed to be:
- **Gradual** — annotations are optional; unannotated code still runs.
- **Incremental** — add verification to critical functions without rewriting everything.
- **Lightweight** — no external solver required for basic guarantees.
- **Extensible** — plugins can add custom verification passes via `post_parse` hooks.
