"""Haxor REPL — interactive interpreter with history, multiline input,
verification mode toggle, and plugin inspection commands.

Special commands (prefix with /):
  /help       — show this help
  /verify     — toggle static verification before execution
  /plugins    — list loaded plugins
  /env        — dump current environment bindings
  /exit       — quit the REPL
"""
from __future__ import annotations
import sys
import traceback
from typing import Optional

from .interpreter import Interpreter, _to_str
from .verifier import Verifier, Severity
from .plugins import registry
from .errors import HaxorError


BANNER = """\
  _   _
 | | | | __ ___  _____  _ __
 | |_| |/ _` \\ \\/ / _ \\| '__|
 |  _  | (_| |>  < (_) | |
 |_| |_|\\__,_/_/\\_\\___/|_|   v0.1.0

Python-inspired · Formally verified · Extensible
Type /help for REPL commands.  Ctrl-D to exit.
"""


class REPL:
    def __init__(self, verify: bool = False):
        self.interp = Interpreter()
        self.verifier = Verifier(strict=False)
        self.verify = verify
        self._setup_history()

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self) -> None:
        print(BANNER)
        while True:
            try:
                source = self._read_input("hx> ")
            except EOFError:
                print("\nBye!")
                break
            except KeyboardInterrupt:
                print()
                continue
            if not source.strip():
                continue
            if source.strip().startswith('/'):
                try:
                    self._handle_command(source.strip())
                except EOFError:
                    print("\nBye!")
                    return
                continue
            self._execute(source)

    # ── Input ─────────────────────────────────────────────────────────────────

    def _read_input(self, prompt: str) -> str:
        """Read one logical block, handling multiline indented continuations.

        Strategy:
        - If a line ends with ':', we enter block mode: keep reading until
          a blank line is entered (mirrors Python's interactive behaviour).
        - Inside brackets, keep reading regardless of newlines.
        - A trailing '\\' continues to the next line.
        """
        lines = []
        try:
            line = input(prompt)
        except EOFError:
            raise
        lines.append(line)

        while True:
            src = '\n'.join(lines)
            last = lines[-1].rstrip()

            # Open brackets force continuation (implicit line joining)
            bracket_depth = (src.count('(') - src.count(')') +
                             src.count('[') - src.count(']') +
                             src.count('{') - src.count('}'))
            if bracket_depth > 0:
                try:
                    cont = input("... ")
                    lines.append(cont)
                    continue
                except EOFError:
                    break

            # Explicit line continuation
            if last.endswith('\\'):
                try:
                    cont = input("... ")
                    lines[-1] = lines[-1][:-1]  # strip backslash
                    lines.append(cont)
                    continue
                except EOFError:
                    break

            # Block mode: a colon at end of a non-blank line opens a block.
            # Collect lines until a blank line signals the block is done.
            if last.endswith(':'):
                while True:
                    try:
                        cont = input("... ")
                    except EOFError:
                        return '\n'.join(lines)
                    lines.append(cont)
                    if cont == '':
                        break  # blank line → block complete
                    # A nested colon keeps us reading without requiring blank
                break

            break  # single-line statement complete

        return '\n'.join(lines)

    # ── Execution ─────────────────────────────────────────────────────────────

    def _execute(self, source: str) -> None:
        from .lexer import Lexer
        from .parser import Parser

        try:
            tokens = Lexer(source).tokenize()
            tree = Parser(tokens).parse()
        except HaxorError as e:
            print(f"\033[31m{e}\033[0m")
            return
        except Exception as e:
            print(f"\033[31mInternal error: {e}\033[0m")
            return

        if self.verify:
            diags = self.verifier.verify(tree)
            for d in diags:
                color = '\033[33m' if d.severity == Severity.WARNING else '\033[31m'
                if d.severity == Severity.INFO:
                    color = '\033[36m'
                print(f"{color}{d}\033[0m")
            if any(d.severity == Severity.ERROR for d in diags):
                return

        try:
            result = self.interp.visit(tree, self.interp.global_env)
            if result is not None:
                print(_to_str(result))
        except HaxorError as e:
            print(f"\033[31m{e}\033[0m")
        except Exception as e:
            print(f"\033[31mInternal error: {e}\033[0m")
            if '--debug' in sys.argv:
                traceback.print_exc()

    # ── REPL commands ─────────────────────────────────────────────────────────

    def _handle_command(self, cmd: str) -> None:
        parts = cmd.split()
        name = parts[0].lower()
        if name == '/help':
            print(__doc__)
        elif name == '/verify':
            self.verify = not self.verify
            state = "ON" if self.verify else "OFF"
            print(f"Static verification: {state}")
        elif name == '/plugins':
            plugins = registry.loaded_plugins()
            if plugins:
                for p in plugins:
                    print(f"  • {p}")
            else:
                print("No plugins loaded.")
        elif name == '/env':
            snap = self.interp.global_env.snapshot()
            for k, v in sorted(snap.items()):
                print(f"  {k} = {_to_str(v)!r}")
        elif name == '/load':
            if len(parts) < 2:
                print("Usage: /load <plugin_path>")
            else:
                try:
                    name = registry.load_from_path(parts[1])
                    # Refresh builtins after plugin load
                    for bn, bfn in registry.get_builtins().items():
                        self.interp.global_env.define(bn, bfn)
                    print(f"Loaded plugin: {name}")
                except Exception as e:
                    print(f"Error loading plugin: {e}")
        elif name in ('/exit', '/quit', '/q'):
            raise EOFError
        else:
            print(f"Unknown command {name!r}. Type /help for help.")

    # ── History ───────────────────────────────────────────────────────────────

    def _setup_history(self) -> None:
        try:
            import readline
            import os
            hist = os.path.expanduser('~/.haxor_history')
            try:
                readline.read_history_file(hist)
            except FileNotFoundError:
                pass
            import atexit
            atexit.register(readline.write_history_file, hist)
            readline.set_history_length(1000)
        except ImportError:
            pass
