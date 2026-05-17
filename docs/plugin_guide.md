# Haxor Plugin Guide

## Architecture overview

The plugin system is built around a singleton `PluginRegistry` accessible at:

```python
from haxor.plugins import registry
```

Plugins interact with the registry through three mechanisms:
1. **Hooks** — callbacks fired at pipeline events
2. **Builtins** — globally available Haxor functions
3. **Modules** — importable Haxor modules (`import my_module`)

---

## Writing a plugin

### Minimal plugin

```python
# my_plugin.py
from haxor.plugins import Plugin, PluginRegistry

class MyPlugin(Plugin):
    PLUGIN_NAME = "my_plugin"

    def register(self, reg: PluginRegistry) -> None:
        reg.register_builtin("greet", lambda name: print(f"Hello, {name}!"))
```

### Plugin as a module

```python
# my_plugin/__init__.py
from .plugin import MyPlugin
__all__ = ["MyPlugin"]

# my_plugin/plugin.py
from haxor.plugins import Plugin
class MyPlugin(Plugin):
    PLUGIN_NAME = "my_plugin"
    def register(self, reg): ...
```

---

## Hooks

### `post_lex`

```python
def my_post_lex(tokens):
    # tokens is a List[Token] — can be inspected but not mutated safely
    print(f"Tokenized {len(tokens)} tokens")

reg.on("post_lex", my_post_lex)
```

### `post_parse`

```python
def my_post_parse(tree):
    # tree is a Program AST node
    print(f"Parsed {len(tree.body)} top-level statements")

reg.on("post_parse", my_post_parse)
```

### `post_execute`

```python
def my_post_execute(result):
    print(f"Program returned: {result}")

reg.on("post_execute", my_post_execute)
```

---

## Adding builtins

```python
import requests  # example: HTTP client

def hx_fetch(url: str) -> str:
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text

reg.register_builtin("fetch", hx_fetch)
```

In Haxor:
```haxor
let html = fetch("https://example.com")
print(len(html))
```

---

## Adding importable modules

```python
from haxor.interpreter import HaxorModule
from haxor.environment import Environment

env = Environment()
env.define("VERSION", "1.0")
env.define("hello", lambda: print("Hi from my_mod!"))

reg.register_module("my_mod", HaxorModule("my_mod", env))
```

In Haxor:
```haxor
import my_mod
print(my_mod.VERSION)
my_mod.hello()
```

---

## Plugin lifecycle

```python
# Load
registry.load(MyPlugin())
registry.load_from_path("path/to/plugin")  # loads from filesystem

# Inspect
print(registry.loaded_plugins())

# Unload (calls plugin.unregister if defined)
registry.unload("my_plugin")
```

---

## Best practices

1. **Name your plugin** via `PLUGIN_NAME` — avoids collisions.
2. **Implement `unregister()`** to clean up hooks when unloaded.
3. **Namespace your builtins**: `my_plugin_fn` not `fn`.
4. **Don't mutate the token stream** in `post_lex` — the parser has already been handed the tokens list by reference; unexpected mutations cause parse errors.
5. **Use `reg.on` not direct `reg._hooks` access** — the public API is stable, internals are not.
