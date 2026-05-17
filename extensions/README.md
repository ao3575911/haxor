# Haxor Extensions

Extensions are Python packages that implement the Haxor plugin API.
They can add builtins, importable modules, or hook into the language pipeline.

## Structure of a plugin

```
my_plugin/
├── __init__.py      # exports MyPlugin class
└── plugin.py        # implementation
```

```python
# plugin.py
from haxor.plugins import Plugin, PluginRegistry

class MyPlugin(Plugin):
    PLUGIN_NAME = "my_plugin"

    def register(self, reg: PluginRegistry) -> None:
        # Add a builtin function
        reg.register_builtin("hello", lambda: print("Hello from MyPlugin!"))

        # Add an importable module
        from haxor.interpreter import HaxorModule
        from haxor.environment import Environment
        env = Environment()
        env.define("answer", 42)
        reg.register_module("my_module", HaxorModule("my_module", env))

        # Hook into the pipeline
        reg.on("post_parse", lambda tree: print(f"Parsed {len(tree.body)} statements"))
```

## Loading plugins

**CLI:**
```bash
haxor run myfile.hx --plugin extensions/my_plugin
```

**Python API:**
```python
from haxor.plugins import registry
registry.load_from_path("extensions/my_plugin")
```

**REPL:**
```
hx> /load extensions/my_plugin
```

## Available hooks

| Event | Args | Description |
|-------|------|-------------|
| `post_lex` | `tokens: List[Token]` | After tokenization |
| `post_parse` | `tree: Program` | After parsing |
| `pre_execute` | `source: str` | Before execution (may rewrite source) |
| `post_execute` | `result: Any` | After execution |

## Included extensions

### `async_plugin`
Adds async/concurrency primitives:
- `sleep(seconds)` — pause execution
- `parallel([fn1, fn2, ...])` — run functions concurrently, collect results
- `future(fn)` — run fn in background, `.get()` to await result
- `timeout(fn, seconds)` — run fn with time limit

```bash
haxor run myfile.hx --plugin extensions/async_plugin
```
