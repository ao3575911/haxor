# Haxor Language Specification v0.1

## Overview

Haxor is an indentation-sensitive, expression-oriented language with Python-compatible
syntax, optional type annotations, and built-in formal verification.

---

## Syntax conventions

- Blocks are delimited by indentation (4 spaces or 1 tab = 4 spaces).
- Statements end at newlines; explicit continuation with `\` or inside brackets.
- Comments begin with `#` and run to end-of-line.
- Identifiers: `[a-zA-Z_][a-zA-Z0-9_]*`

---

## Variables

```haxor
let x = 42                  # declare and bind
let name: str = "Haxor"     # with optional type annotation
x = 100                     # reassign existing variable
x += 1                      # augmented assignment (+= -= *= /= //= %= **=)
```

Bare assignment (`x = value`) creates the variable in the current scope if it
does not exist (Python semantics), or updates the nearest binding if it does.
`let` is the explicit declaration form; prefer it at block scope.

---

## Types

| Haxor name | Python type | Notes |
|------------|-------------|-------|
| `int`      | `int`       | Arbitrary precision |
| `float`    | `float`     | IEEE 754 double |
| `bool`     | `bool`      | `True` / `False` |
| `str`      | `str`       | Unicode |
| `None`     | `None`      | The null value |
| `list`     | `list`      | Mutable sequence `[a, b, c]` |
| `dict`     | `dict`      | Hash map `{"k": v}` |
| `tuple`    | `tuple`     | Immutable sequence `(a, b)` |
| `set`      | `set`       | Unordered unique `{a, b}` |

Type annotations are optional and used by the verifier, not enforced at runtime.

---

## Literals

```haxor
42          0xFF        0b1010      1_000_000   # integers
3.14        1.5e-3                              # floats
"hello"     'world'                             # strings
f"x = {x}" f"sum = {a + b}"                    # f-strings
True        False       None                    # boolean / null
[1, 2, 3]               # list literal
{"a": 1}                # dict literal
(1, 2, 3)               # tuple literal
{1, 2, 3}               # set literal
```

---

## Operators

| Category | Operators |
|----------|-----------|
| Arithmetic | `+ - * / // % **` |
| Bitwise | `& \| ^ ~ << >>` |
| Comparison | `== != < > <= >=` |
| Membership | `in  not in` |
| Identity | `is  is not` |
| Logical | `and  or  not` |
| Augmented assign | `+= -= *= /= //= %= **=` |

Precedence follows Python's standard table (power binds tightest after postfix).

---

## Functions

```haxor
fn greet(name):
    return f"Hello, {name}!"

# With type annotations
fn add(a: int, b: int) -> int:
    return a + b

# Anonymous (expression body)
let double = fn(x): x * 2

# Lambda syntax
let triple = lambda x: x * 3

# Closures capture enclosing scope
fn make_counter():
    let n = 0
    fn increment():
        n += 1
        return n
    return increment
```

---

## Conditionals

```haxor
if condition:
    ...
elif other_condition:
    ...
else:
    ...

# Ternary expression
let sign = "pos" if x > 0 else "non-pos"
```

---

## Loops

```haxor
for item in iterable:
    ...

for i in range(10):
    ...

while condition:
    ...

# List comprehension
let squares = [x * x for x in range(10)]
let evens   = [x for x in range(20) if x % 2 == 0]

# Loop control
break       # exit loop
continue    # skip to next iteration
```

---

## Classes

```haxor
class Animal:
    fn init(self, name):
        self.name = name

    fn speak(self):
        return "..."

class Dog(Animal):
    fn speak(self):
        return f"Woof! I'm {self.name}"

let d = Dog("Rex")
print(d.speak())       # Woof! I'm Rex
print(isinstance(d, "Dog"))  # True
```

- `init` is the constructor (like Python's `__init__`).
- Inheritance is single or multiple: `class C(A, B):`.
- Method resolution follows MRO (left to right through bases).
- `self` must be the first parameter of every instance method.

---

## Imports

```haxor
import math
import math.constants      # dotted module
from math import sqrt
from math import sqrt, pi
from stdlib import *       # wildcard import
```

---

## Formal verification

```haxor
@verify(pre="x > 0", post="result > 0")
fn sqrt_approx(x: float) -> float:
    return x ** 0.5
```

`@verify` accepts keyword arguments:
- `pre` — precondition string evaluated before the call.  The argument names
  in the function signature are bound as variables.
- `post` — postcondition string evaluated after the call.  The return value is
  bound as `result`.
- `invariant` — loop invariant (future).

Conditions are Haxor expressions. Runtime violation raises `VerificationError`.

The static verifier (`haxor verify file.hx`) runs three passes before execution:
1. **Type inference** — warns on annotation mismatches.
2. **Sign analysis** — detects division by zero, sign contradictions.
3. **Control-flow analysis** — warns on missing returns, dead code.

---

## Builtins

`print`, `input`, `len`, `range`, `type`, `isinstance`,
`str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`,
`abs`, `min`, `max`, `sum`, `round`, `sorted`, `reversed`,
`enumerate`, `zip`, `map`, `filter`, `any`, `all`,
`open`, `hash`, `id`, `ord`, `chr`, `hex`, `oct`, `bin`,
`pow`, `divmod`, `repr`, `exit`, `vars`, `dir`,
`getattr`, `setattr`, `hasattr`, `format`, `iter`, `next`, `callable`

---

## Standard library modules

| Module | Contents |
|--------|----------|
| `math` | `sqrt`, `pi`, `e`, `sin`, `cos`, `log`, … |
| `io` | `read_line`, `read_file`, `write_file`, `print_err` |
| `collections` | `OrderedDict`, `Counter`, `flatten`, `chunk`, `unique` |
| `string` | `join`, `split`, `strip`, `upper`, `lower`, `re_match` |
| `os` | `path_join`, `getcwd`, `listdir`, `environ` |
| `random` | `random`, `randint`, `choice`, `shuffle`, `sample` |
| `time` | `time`, `sleep`, `perf_counter` |
| `json` | `dumps`, `loads`, `dump`, `load` |

---

## REPL commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/verify` | Toggle static verification |
| `/plugins` | List loaded plugins |
| `/env` | Dump current environment |
| `/load <path>` | Load a plugin |
| `/exit` | Quit |
