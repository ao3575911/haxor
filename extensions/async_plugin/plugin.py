"""Async plugin: adds sleep(), parallel(), and future primitives to Haxor.

Usage:
    haxor run myfile.hx --plugin extensions/async_plugin

Or from Python:
    from haxor.plugins import registry
    from extensions.async_plugin import AsyncPlugin
    registry.load(AsyncPlugin())

Then in Haxor:
    import async
    async.sleep(0.1)
    let result = async.parallel([fn(): heavy_task(1), fn(): heavy_task(2)])
"""
from __future__ import annotations
import threading
import time
from haxor.plugins import Plugin, PluginRegistry
from haxor.interpreter import HaxorModule
from haxor.environment import Environment


class AsyncPlugin(Plugin):
    PLUGIN_NAME = "async"

    def register(self, reg: PluginRegistry) -> None:
        env = Environment()
        self._populate_env(env, reg)
        mod = HaxorModule("async", env)
        reg.register_module("async", mod)

        # Also register as top-level builtins
        reg.register_builtin("sleep", time.sleep)
        reg.register_builtin("parallel", self._parallel)

        print("[async plugin] registered: sleep, parallel, future")

    def _populate_env(self, env: Environment, reg: PluginRegistry) -> None:
        env.define("sleep", time.sleep)
        env.define("parallel", self._parallel)
        env.define("future", self._make_future)
        env.define("timeout", self._timeout)

    @staticmethod
    def _parallel(funcs: list, *args) -> list:
        """Run a list of zero-argument Haxor functions concurrently."""
        results = [None] * len(funcs)
        errors = [None] * len(funcs)

        def run_fn(i, fn):
            try:
                from haxor.interpreter import _call_value
                results[i] = _call_value(fn, [], {}, 0, None)
            except Exception as e:
                errors[i] = e

        threads = [threading.Thread(target=run_fn, args=(i, fn))
                   for i, fn in enumerate(funcs)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i, err in enumerate(errors):
            if err is not None:
                raise err
        return results

    @staticmethod
    def _make_future(fn) -> '_Future':
        return _Future(fn)

    @staticmethod
    def _timeout(fn, seconds: float):
        """Run fn with a timeout; returns None if it exceeds the limit."""
        result = [None]
        finished = threading.Event()

        def run():
            from haxor.interpreter import _call_value
            try:
                result[0] = _call_value(fn, [], {}, 0, None)
            finally:
                finished.set()

        t = threading.Thread(target=run, daemon=True)
        t.start()
        finished.wait(timeout=seconds)
        return result[0]

    def unregister(self, reg: PluginRegistry) -> None:
        print("[async plugin] unregistered")


class _Future:
    """A simple future backed by a daemon thread."""

    def __init__(self, fn):
        self._result = None
        self._error = None
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(fn,), daemon=True)
        self._thread.start()

    def _run(self, fn):
        try:
            from haxor.interpreter import _call_value
            self._result = _call_value(fn, [], {}, 0, None)
        except Exception as e:
            self._error = e
        finally:
            self._done.set()

    def get(self, timeout=None):
        self._done.wait(timeout=timeout)
        if self._error:
            raise self._error
        return self._result

    def is_done(self) -> bool:
        return self._done.is_set()

    def __repr__(self) -> str:
        state = "done" if self.is_done() else "pending"
        return f"<Future [{state}]>"
