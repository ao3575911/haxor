"""Haxor — A minimal, formally-verifiable programming language for 2030.

Quick start:
    from haxor import run, run_file, REPL

    run('print("Hello, Haxor!")')
    run_file('program.hx')
    REPL().run()
"""
from .interpreter import Interpreter
from .verifier import Verifier
from .plugins import registry, Plugin
from .repl import REPL
from .errors import (
    HaxorError, LexError, ParseError, HaxorRuntimeError,
    HaxorTypeError, HaxorNameError, VerificationError, PluginError,
)
from . import stdlib  # ensure stdlib loaders are registered

__version__ = "0.1.0"
__all__ = [
    "run", "run_file", "parse", "verify",
    "Interpreter", "Verifier", "REPL",
    "registry", "Plugin",
    "HaxorError", "LexError", "ParseError", "HaxorRuntimeError",
    "HaxorTypeError", "HaxorNameError", "VerificationError", "PluginError",
]


def run(source: str, verify: bool = False) -> object:
    """Execute a string of Haxor source code."""
    interp = Interpreter()
    if verify:
        tree = parse(source)
        diags = Verifier().verify(tree)
        errors = [d for d in diags if d.severity.name == 'ERROR']
        if errors:
            from .errors import VerificationError as VE
            raise VE('\n'.join(str(d) for d in errors))
    return interp.execute(source)


def run_file(path: str, verify: bool = False) -> object:
    """Execute a .hx file."""
    with open(path, encoding='utf-8') as f:
        return run(f.read(), verify=verify)


def parse(source: str):
    """Lex and parse *source*, returning the AST Program node."""
    from .lexer import Lexer
    from .parser import Parser
    return Parser(Lexer(source).tokenize()).parse()


def verify(source: str, strict: bool = False):
    """Run all static analysis passes and return a list of Diagnostics."""
    tree = parse(source)
    return Verifier(strict=strict).verify(tree)
