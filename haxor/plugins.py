"""Plugin architecture for Haxor.

Plugins are Python objects (classes or modules) that implement a `register(registry)`
method.  The registry exposes hook points, a builtin table, and a module table.

Hook events:
  - 'post_lex'      (tokens: List[Token]) -> None
  - 'post_parse'    (tree: Program)       -> None
  - 'pre_execute'   (source: str)         -> Optional[str]  (may rewrite source)
  - 'post_execute'  (result: Any)         -> None

Plugin authors can also:
  - register_builtin(name, callable)  — add a global built-in function
  - register_module(name, HaxorModule) — add an importable module
"""
from __future__ import annotations
import importlib
import importlib.util
import os
import sys
from typing import Any, Callable, Dict, List, Optional


class PluginRegistry:
    """Singleton registry; access via the module-level `registry` instance."""

    _instance: Optional['PluginRegistry'] = None

    def __new__(cls) -> 'PluginRegistry':
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._hooks: Dict[str, List[Callable]] = {}
            inst._builtins: Dict[str, Any] = {}
            inst._modules: Dict[str, Any] = {}
            inst._loaded: Dict[str, Any] = {}
            cls._instance = inst
        return cls._instance

    # ── Hooks ─────────────────────────────────────────────────────────────────

    def on(self, event: str, handler: Callable) -> None:
        """Register a hook handler for *event*."""
        self._hooks.setdefault(event, []).append(handler)

    def trigger(self, event: str, *args, **kwargs) -> List[Any]:
        """Fire all handlers for *event*, collecting return values."""
        return [h(*args, **kwargs) for h in self._hooks.get(event, [])]

    def off(self, event: str, handler: Callable) -> None:
        """Unregister a specific handler."""
        if event in self._hooks:
            self._hooks[event] = [h for h in self._hooks[event] if h is not handler]

    # ── Builtins ──────────────────────────────────────────────────────────────

    def register_builtin(self, name: str, func: Callable) -> None:
        self._builtins[name] = func

    def get_builtins(self) -> Dict[str, Any]:
        return dict(self._builtins)

    # ── Modules ───────────────────────────────────────────────────────────────

    def register_module(self, name: str, module: Any) -> None:
        self._modules[name] = module

    def get_module(self, name: str) -> Optional[Any]:
        return self._modules.get(name)

    # ── Plugin loading ────────────────────────────────────────────────────────

    def load(self, plugin: Any) -> str:
        """Load a plugin instance or class; call its register() method."""
        if isinstance(plugin, type):
            plugin = plugin()
        name = getattr(plugin, 'PLUGIN_NAME', type(plugin).__name__)
        if name in self._loaded:
            return name
        if hasattr(plugin, 'register'):
            plugin.register(self)
        self._loaded[name] = plugin
        return name

    def load_from_path(self, path: str) -> str:
        """Import a Python file or package and call its register(registry)."""
        path = os.path.abspath(path)
        if os.path.isdir(path):
            path = os.path.join(path, '__init__.py')
        spec = importlib.util.spec_from_file_location('_haxor_plugin', path)
        if spec is None:
            raise ImportError(f"Cannot load plugin from {path!r}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return self.load(mod)

    def unload(self, name: str) -> None:
        plugin = self._loaded.pop(name, None)
        if plugin and hasattr(plugin, 'unregister'):
            plugin.unregister(self)

    def loaded_plugins(self) -> List[str]:
        return list(self._loaded.keys())

    def __repr__(self) -> str:
        return f"<PluginRegistry plugins={self.loaded_plugins()}>"


# Module-level singleton
registry = PluginRegistry()


# ── Plugin base class (optional convenience) ──────────────────────────────────

class Plugin:
    """Convenience base class — subclass and override register()."""
    PLUGIN_NAME: str = ""

    def register(self, reg: PluginRegistry) -> None:
        raise NotImplementedError

    def unregister(self, reg: PluginRegistry) -> None:
        pass
