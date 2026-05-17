# Haxor

A minimal, open-source programming language inspired by Python — designed for 2030.

```haxor
@verify(pre="n >= 0", post="result >= 0")
fn fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

let seq = [fibonacci(i) for i in range(10)]
print(f"Fibonacci: {seq}")
```

## Why Haxor?

| Feature | Description |
|---------|-------------|
| **Python syntax** | Indentation-based blocks, familiar operators |
| **Formal verification** | `@verify(pre=..., post=...)` contracts, static analysis |
| **Plugin architecture** | Extend the language in Python — add builtins, modules, pipeline hooks |
| **REPL-first** | Interactive development with history, multiline input, verification toggle |
| **< 10k lines** | Read the whole implementation in an afternoon |

## Quick start

```bash
git clone https://github.com/yourname/haxor
cd haxor
pip install -e .            # or: python haxor_cli.py
haxor                       # start REPL
haxor run examples/hello.hx
haxor verify examples/verified.hx
```

No external dependencies required.  Optional: `pip install z3-solver` for SMT-based verification.

## Language at a glance

```haxor
# Variables
let x: int = 42
let name = "world"

# Functions & closures
fn add(a, b): return a + b
let double = fn(x): x * 2
let triple = lambda x: x * 3

# Classes & inheritance
class Animal:
    fn init(self, name):
        self.name = name
    fn speak(self): return "..."

class Dog(Animal):
    fn speak(self): return f"Woof! I'm {self.name}"

# Loops & comprehensions
for i in range(5): print(i)
let evens = [x for x in range(10) if x % 2 == 0]

# Imports
import math
from collections import Counter

# Verification
@verify(pre="x > 0", post="result > 0")
fn sqrt_safe(x): return x ** 0.5
```

## Repository structure

```
haxor/
├── haxor/           Language core
│   ├── lexer.py     Tokenizer (indentation-aware)
│   ├── parser.py    Recursive-descent parser
│   ├── ast_nodes.py AST node definitions
│   ├── interpreter.py Tree-walking interpreter
│   ├── environment.py Lexical scope chain
│   ├── verifier.py  Static analysis (type + sign + flow)
│   ├── plugins.py   Plugin registry & hook system
│   ├── repl.py      Interactive REPL
│   └── stdlib/      Python-backed standard library
├── tests/           pytest test suite
├── examples/        Sample programs
├── extensions/      Plugin examples (async_plugin)
├── docs/            Language spec, plugin guide, verification docs
└── haxor_cli.py     CLI entry point
```

## CLI

```bash
haxor                       # REPL
haxor run file.hx           # run a file
haxor run file.hx --verify  # static analysis + run
haxor verify file.hx        # static analysis only
haxor parse file.hx         # dump AST
haxor run file.hx --plugin extensions/async_plugin
```

## REPL commands

```
/help     — help
/verify   — toggle static verification
/plugins  — list loaded plugins
/env      — show all bindings
/load     — load a plugin file
/exit     — quit
```

## Running tests

```bash
pip install pytest
pytest tests/
pytest tests/ -v --tb=short
```

## Plugin example

```python
# my_plugin.py
from haxor.plugins import Plugin

class MyPlugin(Plugin):
    PLUGIN_NAME = "my_plugin"

    def register(self, reg):
        reg.register_builtin("hello", lambda: print("Hello from plugin!"))
        reg.on("post_parse", lambda tree: print(f"Parsed {len(tree.body)} stmts"))
```

```bash
haxor run myfile.hx --plugin my_plugin.py
```

## Formal verification

```haxor
@verify(pre="0 <= x and x <= 1", post="0 <= result and result <= 1")
fn sigmoid(x):
    import math
    return 1.0 / (1.0 + math.exp(-x))
```

Static passes detect:
- Type annotation mismatches
- Division by zero (sign analysis)
- Missing return paths (control-flow analysis)

## License

MIT © 2030 Haxor Contributors
