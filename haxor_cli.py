#!/usr/bin/env python3
"""haxor — command-line interface for the Haxor language.

Usage:
  haxor                         # Start REPL
  haxor run <file.hx>           # Execute a file
  haxor run <file.hx> --verify  # Execute with static analysis
  haxor verify <file.hx>        # Static analysis only
  haxor parse <file.hx>         # Parse and dump AST
  haxor repl                    # Start REPL (explicit)
  haxor version                 # Print version

Options:
  --verify, -v    Run static analysis before execution
  --strict        Treat analysis warnings as errors
  --plugin PATH   Load a plugin before running
  --debug         Print tracebacks on error
"""
import sys
import os
import argparse

# Allow running from the repo root without installing
sys.path.insert(0, os.path.dirname(__file__))

import haxor
from haxor.repl import REPL
from haxor.verifier import Verifier, Severity
from haxor.plugins import registry
from haxor.errors import HaxorError


def cmd_run(args) -> int:
    for plugin_path in args.plugin:
        registry.load_from_path(plugin_path)

    try:
        haxor.run_file(args.file, verify=args.verify)
        return 0
    except HaxorError as e:
        print(f"\033[31m{e}\033[0m", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"File not found: {args.file}", file=sys.stderr)
        return 1
    except Exception as e:
        if args.debug:
            import traceback; traceback.print_exc()
        else:
            print(f"\033[31mInternal error: {e}\033[0m", file=sys.stderr)
        return 1


def cmd_verify(args) -> int:
    try:
        diags = haxor.verify(open(args.file).read(), strict=args.strict)
    except FileNotFoundError:
        print(f"File not found: {args.file}", file=sys.stderr)
        return 1
    except HaxorError as e:
        print(str(e), file=sys.stderr)
        return 1

    if not diags:
        print(f"\033[32m✓ {args.file}: no issues found\033[0m")
        return 0

    has_error = False
    for d in diags:
        color = {
            'INFO': '\033[36m',
            'WARNING': '\033[33m',
            'ERROR': '\033[31m',
        }.get(d.severity.name, '')
        print(f"{color}{d}\033[0m")
        if d.severity.name == 'ERROR':
            has_error = True
    return 1 if has_error else 0


def cmd_parse(args) -> int:
    try:
        tree = haxor.parse(open(args.file).read())
    except HaxorError as e:
        print(str(e), file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"File not found: {args.file}", file=sys.stderr)
        return 1

    import pprint
    pprint.pprint(tree)
    return 0


def cmd_repl(args) -> int:
    for plugin_path in args.plugin:
        registry.load_from_path(plugin_path)
    REPL(verify=args.verify).run()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog='haxor',
        description='The Haxor programming language',
    )
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--debug', action='store_true')

    subparsers = parser.add_subparsers(dest='command')

    # run
    run_p = subparsers.add_parser('run', help='Execute a .hx file')
    run_p.add_argument('file')
    run_p.add_argument('--verify', '-v', action='store_true')
    run_p.add_argument('--strict', action='store_true')
    run_p.add_argument('--plugin', metavar='PATH', action='append', default=[])
    run_p.add_argument('--debug', action='store_true')

    # verify
    ver_p = subparsers.add_parser('verify', help='Static analysis only')
    ver_p.add_argument('file')
    ver_p.add_argument('--strict', action='store_true')

    # parse
    par_p = subparsers.add_parser('parse', help='Dump AST')
    par_p.add_argument('file')

    # repl
    rep_p = subparsers.add_parser('repl', help='Start interactive REPL')
    rep_p.add_argument('--verify', '-v', action='store_true')
    rep_p.add_argument('--plugin', metavar='PATH', action='append', default=[])

    args = parser.parse_args()

    if args.version or (hasattr(args, 'command') and not args.command and '--version' not in sys.argv):
        if getattr(args, 'version', False):
            print(f"Haxor {haxor.__version__}")
            return 0

    if not args.command:
        # No subcommand → start REPL
        REPL().run()
        return 0

    dispatch = {
        'run': cmd_run,
        'verify': cmd_verify,
        'parse': cmd_parse,
        'repl': cmd_repl,
    }
    handler = dispatch.get(args.command)
    if handler:
        return handler(args)
    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
