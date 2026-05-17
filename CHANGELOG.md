# Changelog

All notable changes to Haxor will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Haxor uses [semantic versioning](https://semver.org/).

## [0.1.0] — 2026-05-17

First public release.

### Added

**Language**
- Variables with `let`, optional type annotations (`let x: int = 42`)
- Functions via `fn`, with default parameters, closures, and recursion
- Lambda expressions (`lambda x: x * 2`) and anonymous functions (`fn(x): x * 2`)
- Classes with single inheritance, instance methods, and `init`
- Control flow: `if`/`elif`/`else`, `while`, `for`/`in`, `break`, `continue`
- List comprehensions with optional filter (`[x for x in lst if cond]`)
- Data structures: lists, dicts, tuples, sets, slices
- f-strings (`f"Hello, {name}!"`) with arbitrary expression interpolation
- Full operator set: arithmetic, comparison, boolean, augmented assignment, `**`, `//`, `%`
- Imports: `import module` and `from module import name`
- `@verify(pre=..., post=...)` decorator for runtime pre/post-condition contracts

**Static verifier** (`haxor verify`, `haxor run --verify`)
- Pass 1: type inference — annotation mismatches, undefined names
- Pass 2: sign-domain abstract interpretation — division by zero
- Pass 3: control-flow analysis — missing `return` in annotated functions
- Optional Z3 SMT backend (`pip install z3-solver`)
- Strict mode (`--strict`) promotes warnings to errors

**Standard library**
- `math`, `io`, `collections`, `string`, `os`, `random`, `time`, `json`
- 50+ built-in functions: `len`, `range`, `type`, `print`, `map`, `filter`, `sorted`, `zip`, `enumerate`, `sum`, `min`, `max`, `abs`, `any`, `all`, and more

**Plugin system**
- `PluginRegistry` singleton with `register_builtin`, `register_module`
- Hooks: `post_lex`, `post_parse`, `post_execute`
- `Plugin` base class for packaged plugins
- CLI flag `--plugin <path>` and REPL `/load <path>` command
- Example: `extensions/async_plugin` — adds `sleep`, `parallel`, `future`, `timeout`

**REPL**
- Multiline block detection (trailing `:`, open brackets, explicit `\`)
- readline history
- `/verify`, `/env`, `/plugins`, `/load`, `/help`, `/exit` commands

**CLI** (`haxor`)
- `haxor run <file>` — execute a `.hx` file
- `haxor verify <file>` — static analysis only
- `haxor parse <file>` — dump AST
- `haxor repl` — explicit REPL entry
- `--verify`, `--strict`, `--plugin`, `--debug` flags

**Infrastructure**
- 179-test pytest suite covering lexer, parser, interpreter, and verifier
- GitHub Actions CI: test matrix (Python 3.10–3.13) + lint (ruff)
- Automated PyPI publish on version tags via OIDC trusted publishing
- Published to PyPI as [`hxr`](https://pypi.org/project/hxr/)
- Docs: `docs/language_spec.md`, `docs/plugin_guide.md`, `docs/verification.md`

[0.1.0]: https://github.com/ao3575911/haxor/releases/tag/v0.1.0
