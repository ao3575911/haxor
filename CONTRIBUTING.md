# Contributing to Haxor

Thanks for your interest in Haxor. This document covers how to get started, what kinds of contributions are welcome, and how to get your changes merged.

## Getting started

```bash
git clone https://github.com/ao3575911/haxor
cd haxor
pip install -e ".[dev]"   # installs pytest
pytest tests/             # all 179 tests should pass
```

No other dependencies are required. `z3-solver` is optional for SMT-based verification.

## What to work on

### Good first issues
- Additional built-in functions (`sorted` with key, `any`/`all` with generators, etc.)
- More stdlib modules (e.g. `functools`, `itertools`)
- Better error messages (line/col in more error types)
- REPL improvements (syntax highlighting, tab completion)
- Additional example programs in `examples/`

### Bigger projects
- Multiple assignment / destructuring: `let a, b = 1, 2`
- `try / except / finally` exception handling
- Generator functions (`yield`)
- Type system improvements (union types, generics)
- Bytecode compiler + VM (replacing the tree-walker)
- LSP server for editor integration
- Package manager (`haxor install`)

## Project layout

```
haxor/          Language core — lexer, parser, AST, interpreter, verifier
haxor/stdlib/   Python-backed standard library modules
tests/          pytest test suite (mirrors haxor/ structure)
examples/       Runnable .hx programs
extensions/     Plugin examples
docs/           Language spec, plugin guide, verification docs
```

See `CLAUDE.md` for a detailed architectural guide before touching core files.

## Making a change

1. **Fork** the repo and create a branch: `git checkout -b my-feature`
2. **Write tests first** — every new language feature or bug fix needs a test in `tests/`.
3. **Run the suite**: `pytest tests/ -v` — it must stay green.
4. **Run the examples**: `python haxor_cli.py run examples/fibonacci.hx` etc.
5. **Open a PR** against `main` with a clear description of what and why.

## Adding a language feature

The typical path through the codebase:

| Step | File | What to do |
|------|------|------------|
| 1 | `haxor/lexer.py` | Add token type(s) to `TT` and handle in `_operator` / `_name` |
| 2 | `haxor/ast_nodes.py` | Add a dataclass node |
| 3 | `haxor/parser.py` | Parse the new syntax into the node |
| 4 | `haxor/interpreter.py` | Add `visit_NodeName` method |
| 5 | `haxor/verifier.py` | Add `_type_NodeName` and `_sign_NodeName` stubs |
| 6 | `tests/` | Cover the new feature in the appropriate test file |

## Adding a stdlib module

Add a `@_register('module_name')` loader in `haxor/stdlib/__init__.py`:

```python
@_register('mymod')
def _load_mymod(env, interp):
    env.define('hello', lambda: print("hi from mymod"))
```

Then it's importable in Haxor: `from mymod import hello`.

## Writing a plugin

See `docs/plugin_guide.md` and `extensions/async_plugin/` for a full example.
Plugins live outside the core repo — link yours in a GitHub Discussion so others can find it.

## Code style

- Standard Python (no formatter enforced, but keep it readable).
- No comments that restate what the code does — only comments for non-obvious *why*.
- Keep functions short; the existing visitors are good examples of the target style.
- Match the line-length and indentation of surrounding code.

## Tests

- `tests/test_lexer.py` — token-level checks
- `tests/test_parser.py` — AST shape checks (no execution)
- `tests/test_interpreter.py` — end-to-end execution via `run_get(src, varname)`
- `tests/test_verifier.py` — static analysis diagnostic checks

New interpreter features go in `TestInterpreter` classes that match the feature area. New syntax goes in both `test_parser.py` and `test_interpreter.py`.

## Reporting bugs

Open a GitHub Issue with:
- The Haxor source that triggers the bug (minimal reproduction)
- Expected vs. actual output
- Python version (`python --version`)
