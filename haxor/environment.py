"""Lexical environment (scope chain) for the Haxor interpreter."""
from __future__ import annotations
from typing import Any, Optional
from .errors import HaxorNameError


class Environment:
    """Single scope frame; parent chain implements lexical scoping."""

    __slots__ = ("_store", "parent")

    def __init__(self, parent: Optional[Environment] = None):
        self._store: dict[str, Any] = {}
        self.parent = parent

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, name: str, line: int = 0) -> Any:
        env = self._resolve(name)
        if env is None:
            raise HaxorNameError(f"'{name}' is not defined", line)
        return env._store[name]

    def _resolve(self, name: str) -> Optional[Environment]:
        if name in self._store:
            return self
        if self.parent is not None:
            return self.parent._resolve(name)
        return None

    # ── Write ─────────────────────────────────────────────────────────────────

    def define(self, name: str, value: Any) -> None:
        """Bind name in *this* scope (used by let, fn, class, for-targets)."""
        self._store[name] = value

    def assign(self, name: str, value: Any, line: int = 0) -> None:
        """Assign to an already-declared variable anywhere in the scope chain."""
        env = self._resolve(name)
        if env is None:
            # Haxor allows bare assignment to implicitly create in current scope
            # (Python semantics) — emitted as a warning by the verifier.
            self._store[name] = value
        else:
            env._store[name] = value

    # ── Utility ───────────────────────────────────────────────────────────────

    def child(self) -> Environment:
        return Environment(parent=self)

    def snapshot(self) -> dict:
        """Flat snapshot of all visible bindings (for REPL inspection)."""
        result = {}
        env: Optional[Environment] = self
        while env is not None:
            for k, v in env._store.items():
                result.setdefault(k, v)
            env = env.parent
        return result

    def __repr__(self) -> str:
        keys = list(self._store.keys())
        return f"<Environment {keys}>"
