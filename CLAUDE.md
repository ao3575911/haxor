# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run a Haxor program
python haxor_cli.py run examples/hello.hx
python haxor_cli.py run examples/fibonacci.hx --verify

# Static analysis only
python haxor_cli.py verify examples/verified.hx

# Interactive REPL
python haxor_cli.py

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_interpreter.py -v

# Run a single test
pytest tests/test_interpreter.py::TestFunctions::test_closure -v

# Install in editable mode (enables `haxor` CLI)
pip install -e .
```

## Architecture

The pipeline is: **source → Lexer → Parser → AST → Interpreter** (tree-walking).
The Verifier runs as a separate pass over the AST before execution when requested.

### Core modules (`haxor/`)

| File | Role |
|------|------|
| `lexer.py` | Tokenizer. Tracks indentation with a stack; emits `INDENT`/`DEDENT` tokens. Implicit line continuation inside brackets via `bracket_depth`. |
| `parser.py` | Recursive-descent parser. `_expr()` → `_ternary()` → `_or_expr()` → … → `_primary()` implements precedence climbing. `_indented_block()` consumes `COLON NEWLINE INDENT body DEDENT`. |
| `ast_nodes.py` | Frozen dataclasses for every node type. All nodes carry `line`/`col` for error reporting. |
| `interpreter.py` | Visitor dispatch via `visit_{ClassName}`. `HaxorFunction`, `HaxorClass`, `HaxorInstance`, `BoundMethod` are the core runtime value types. Control flow uses `_Return`/`_Break`/`_Continue` exceptions. |
| `environment.py` | Lexical scope chain: `define()` binds in current frame, `assign()` walks the chain, `get()` raises `HaxorNameError`. |
| `verifier.py` | Three-pass static analyser: (1) type inference, (2) sign-domain abstract interpretation, (3) CFG-based missing-return detection. Optional Z3 for SMT checks. |
| `plugins.py` | Singleton `PluginRegistry`. Hooks: `post_lex`, `post_parse`, `post_execute`. `register_builtin` / `register_module` extend the language. |
| `repl.py` | REPL with readline history, multiline block detection (trailing `:`, open brackets), `/`-prefixed meta-commands. |
| `stdlib/__init__.py` | Python-implemented stdlib loaders registered in `_MODULE_LOADERS`. Each loader populates an `Environment` for `HaxorModule`. |
| `stdlib/_builtins.py` | All global built-in functions. Returned by `get_builtins(interp)` and registered into `global_env` at interpreter startup. |

### Key invariants

- `@verify(pre=..., post=...)` pre/post conditions are re-parsed as Haxor expressions at call time via a nested `Lexer` + `Parser` invocation.
- `HaxorClass.__call__` instantiates `HaxorInstance` then calls the `init` method if present.
- `BoundMethod.call` prepends `self` to the arg list and delegates to `HaxorFunction.call`.
- The `PluginRegistry` is a singleton — tests that load plugins will share state unless they call `PluginRegistry._instance = None` to reset.

### Extending the language

- **New builtin**: add to `stdlib/_builtins.py::get_builtins` or `registry.register_builtin`.
- **New stdlib module**: add a `@_register('name')` loader in `stdlib/__init__.py`.
- **New syntax**: add tokens to `lexer.py`, AST nodes to `ast_nodes.py`, a parse method to `parser.py`, and a `visit_*` method to `interpreter.py`.
- **New plugin**: subclass `Plugin` from `haxor/plugins.py`, implement `register(reg)`.

### Testing patterns

- `run_get(src, varname)` — execute source, read a variable from global env.
- `parse(src)` / `parse_expr(src)` — test AST shape without execution.
- `verify(src)` / `errors(diags)` / `warnings(diags)` — test static analysis.
- Verification error tests use `pytest.raises(VerificationError)`.
