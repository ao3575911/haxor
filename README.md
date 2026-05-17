# Haxor

[![CI](https://github.com/ao3575911/haxor/actions/workflows/ci.yml/badge.svg)](https://github.com/ao3575911/haxor/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/hxr?cachSeconds=0)](https://pypi.org/project/hxr/)
[![GitHub Release](https://img.shields.io/github/v/release/ao3575911/haxor)](https://github.com/ao3575911/haxor/releases/latest)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Discussions](https://img.shields.io/github/discussions/ao3575911/haxor)](https://github.com/ao3575911/haxor/discussions)

**Haxor** is a minimal, open-source programming language inspired by Python — built for 2030. It fits in under 10,000 lines, runs interactively in a REPL, and ships with a static verifier and a plugin system.

```haxor
@verify(pre="n >= 0", post="result >= 0")
fn fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

let seq = [fibonacci(i) for i in range(10)]
print(f"Fibonacci: {seq}")
```

## Highlights

| | |
|---|---|
| **Familiar syntax** | Indentation-based blocks, Python-style operators |
| **Static verifier** | Type inference, sign analysis, missing-return detection |
| **Runtime contracts** | `@verify(pre=..., post=...)` checked at call time |
| **Plugin system** | Add builtins, modules, and pipeline hooks from Python |
| **REPL** | Multiline input, history, inline verification, `/`-commands |
| **No dependencies** | Pure Python — just `pip install hxr` |

## Installation

```bash
pip install hxr
```

Optional SMT-based verification:

```bash
pip install hxr z3-solver
```

To run from source:

```bash
git clone https://github.com/ao3575911/haxor
cd haxor
pip install -e .
```

## Quick start

```bash
haxor                        # start the REPL
haxor run examples/hello.hx  # run a file
haxor run file.hx --verify   # run with static analysis
haxor verify file.hx         # static analysis only
```

## Language overview

```haxor
# Variables with optional type annotations
let x: int = 42
let name = "Haxor"

# Functions, lambdas, and closures
fn add(a, b): return a + b
fn make_adder(n):
    return lambda x: x + n
let add5 = make_adder(5)

# Classes and inheritance
class Animal:
    fn init(self, name):
        self.name = name

class Dog(Animal):
    fn speak(self):
        return f"Woof! I'm {self.name}"

d = Dog("Rex")
print(d.speak())

# Loops and comprehensions
let evens = [x for x in range(10) if x % 2 == 0]

# Imports
import math
from collections import Counter

# Runtime contracts
@verify(pre="x > 0", post="result > 0")
fn sqrt_safe(x):
    return x ** 0.5
```

## Static verifier

Run `haxor verify file.hx` to catch issues before execution:

- **Type inference** — flags annotation mismatches and undefined names
- **Sign analysis** — detects division by zero via abstract interpretation
- **Control-flow analysis** — warns on functions with missing `return` paths

```bash
$ haxor verify examples/verified.hx
✓ examples/verified.hx: no issues found
```

## Plugin system

```python
# my_plugin.py
from haxor.plugins import Plugin

class MyPlugin(Plugin):
    PLUGIN_NAME = "my_plugin"

    def register(self, reg):
        reg.register_builtin("greet", lambda name: f"Hello, {name}!")
        reg.on("post_execute", lambda env: print("done"))
```

```bash
haxor run file.hx --plugin my_plugin.py
```

Available hooks: `post_lex`, `post_parse`, `post_execute`. See [`extensions/async_plugin/`](extensions/async_plugin/) for a full example.

## REPL commands

| Command | Description |
|---------|-------------|
| `/verify` | Toggle static analysis on each input |
| `/env` | Show all current bindings |
| `/plugins` | List loaded plugins |
| `/load <path>` | Load a plugin at runtime |
| `/help` | Show all commands |
| `/exit` | Quit |

## Repository layout

```
haxor/
├── haxor/            Language core
│   ├── lexer.py      Indentation-aware tokenizer
│   ├── parser.py     Recursive-descent parser
│   ├── ast_nodes.py  AST node definitions
│   ├── interpreter.py Tree-walking interpreter
│   ├── verifier.py   Static analysis (type + sign + flow)
│   ├── plugins.py    Plugin registry and hooks
│   ├── repl.py       Interactive REPL
│   └── stdlib/       Python-backed standard library
├── tests/            pytest suite (179 tests)
├── examples/         Sample programs
├── extensions/       Plugin examples
├── docs/             Language spec, plugin guide, verification docs
└── haxor_cli.py      CLI entry point
```

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Join the conversation in [Discussions](https://github.com/ao3575911/haxor/discussions).

## License

MIT © 2026 Haxor Contributors
