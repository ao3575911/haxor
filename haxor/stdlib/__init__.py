"""Haxor standard library — Python-implemented module loaders.

Each entry in _MODULE_LOADERS maps a dotted module name to a loader function:
    loader(env: Environment, interp: Interpreter) -> None

The loader populates *env* with the module's exported names.
"""
from __future__ import annotations

_MODULE_LOADERS = {}


def _register(name):
    def decorator(fn):
        _MODULE_LOADERS[name] = fn
        return fn
    return decorator


# ── math module ───────────────────────────────────────────────────────────────

@_register('math')
def _load_math(env, interp):
    import math as _m
    for name in ('sqrt', 'floor', 'ceil', 'log', 'log2', 'log10',
                 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',
                 'exp', 'pow', 'fabs', 'factorial', 'gcd', 'lcm',
                 'degrees', 'radians', 'isnan', 'isinf', 'isfinite',
                 'hypot', 'copysign', 'trunc'):
        if hasattr(_m, name):
            env.define(name, getattr(_m, name))
    env.define('pi', _m.pi)
    env.define('e', _m.e)
    env.define('tau', _m.tau)
    env.define('inf', _m.inf)
    env.define('nan', _m.nan)
    env.define('abs', abs)


# ── io module ─────────────────────────────────────────────────────────────────

@_register('io')
def _load_io(env, interp):
    import sys as _sys

    def read_line(prompt=''):
        return input(prompt)

    def read_file(path):
        with open(path, encoding='utf-8') as f:
            return f.read()

    def write_file(path, content):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(str(content))

    def print_err(*args, sep=' ', end='\n'):
        print(*args, sep=sep, end=end, file=_sys.stderr)

    env.define('read_line', read_line)
    env.define('read_file', read_file)
    env.define('write_file', write_file)
    env.define('print_err', print_err)
    env.define('stdin', _sys.stdin)
    env.define('stdout', _sys.stdout)
    env.define('stderr', _sys.stderr)


# ── collections module ────────────────────────────────────────────────────────

@_register('collections')
def _load_collections(env, interp):
    from collections import OrderedDict, defaultdict, deque, Counter

    env.define('OrderedDict', OrderedDict)
    env.define('defaultdict', defaultdict)
    env.define('deque', deque)
    env.define('Counter', Counter)

    def flatten(lst):
        result = []
        for item in lst:
            if isinstance(item, (list, tuple)):
                result.extend(flatten(item))
            else:
                result.append(item)
        return result

    def chunk(lst, size):
        return [lst[i:i + size] for i in range(0, len(lst), size)]

    def unique(lst):
        seen = set()
        return [x for x in lst if not (x in seen or seen.add(x))]

    env.define('flatten', flatten)
    env.define('chunk', chunk)
    env.define('unique', unique)


# ── string module ─────────────────────────────────────────────────────────────

@_register('string')
def _load_string(env, interp):
    import string as _s
    import re as _re

    env.define('ascii_letters', _s.ascii_letters)
    env.define('ascii_lowercase', _s.ascii_lowercase)
    env.define('ascii_uppercase', _s.ascii_uppercase)
    env.define('digits', _s.digits)
    env.define('punctuation', _s.punctuation)
    env.define('whitespace', _s.whitespace)

    env.define('join', lambda sep, lst: sep.join(str(x) for x in lst))
    env.define('split', lambda s, sep=None: s.split(sep))
    env.define('strip', lambda s, chars=None: s.strip(chars))
    env.define('upper', lambda s: s.upper())
    env.define('lower', lambda s: s.lower())
    env.define('replace', lambda s, old, new: s.replace(old, new))
    env.define('startswith', lambda s, prefix: s.startswith(prefix))
    env.define('endswith', lambda s, suffix: s.endswith(suffix))
    env.define('format', lambda template, *args, **kwargs: template.format(*args, **kwargs))
    env.define('re_match', lambda pattern, s: bool(_re.match(pattern, s)))
    env.define('re_find', lambda pattern, s: _re.findall(pattern, s))
    env.define('re_sub', lambda pattern, repl, s: _re.sub(pattern, repl, s))


# ── os module ────────────────────────────────────────────────────────────────

@_register('os')
def _load_os(env, interp):
    import os as _os
    env.define('path_join', _os.path.join)
    env.define('path_exists', _os.path.exists)
    env.define('path_dirname', _os.path.dirname)
    env.define('path_basename', _os.path.basename)
    env.define('getcwd', _os.getcwd)
    env.define('listdir', _os.listdir)
    env.define('environ', dict(_os.environ))
    env.define('getenv', _os.environ.get)
    env.define('sep', _os.sep)


# ── random module ─────────────────────────────────────────────────────────────

@_register('random')
def _load_random(env, interp):
    import random as _r
    env.define('random', _r.random)
    env.define('randint', _r.randint)
    env.define('choice', _r.choice)
    env.define('choices', _r.choices)
    env.define('shuffle', _r.shuffle)
    env.define('sample', _r.sample)
    env.define('seed', _r.seed)
    env.define('uniform', _r.uniform)


# ── time module ───────────────────────────────────────────────────────────────

@_register('time')
def _load_time(env, interp):
    import time as _t
    env.define('time', _t.time)
    env.define('sleep', _t.sleep)
    env.define('perf_counter', _t.perf_counter)
    env.define('strftime', _t.strftime)
    env.define('localtime', _t.localtime)
    env.define('gmtime', _t.gmtime)


# ── json module ───────────────────────────────────────────────────────────────

@_register('json')
def _load_json(env, interp):
    import json as _j
    env.define('dumps', _j.dumps)
    env.define('loads', _j.loads)
    env.define('dump', _j.dump)
    env.define('load', _j.load)
