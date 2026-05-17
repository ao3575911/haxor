"""Global built-in functions available in every Haxor program."""
from __future__ import annotations
import sys
from typing import Any, Dict


def get_builtins(interp) -> Dict[str, Any]:
    """Return a dict of all built-in names for the given interpreter instance."""

    def hx_print(*args, sep=' ', end='\n'):
        from ..interpreter import _to_str
        print(sep.join(_to_str(a) for a in args), end=end)

    def hx_input(prompt=''):
        return input(str(prompt))

    def hx_len(obj):
        try:
            return len(obj)
        except TypeError:
            from ..errors import HaxorTypeError
            raise HaxorTypeError(f"Object of type '{type(obj).__name__}' has no len()")

    def hx_range(*args):
        return list(range(*[int(a) for a in args]))

    def hx_type(obj):
        from ..interpreter import HaxorInstance, HaxorClass, HaxorFunction, BoundMethod
        if isinstance(obj, HaxorInstance): return obj.cls.name
        if isinstance(obj, HaxorClass): return f"<class '{obj.name}'>"
        if isinstance(obj, (HaxorFunction, BoundMethod)): return 'function'
        return type(obj).__name__

    def hx_isinstance(obj, cls_name):
        from ..interpreter import HaxorInstance
        if isinstance(obj, HaxorInstance):
            # Walk MRO
            def check(c):
                if c.name == cls_name:
                    return True
                return any(check(b) for b in c.bases)
            return check(obj.cls)
        type_map = {
            'int': int, 'float': float, 'str': str,
            'bool': bool, 'list': list, 'dict': dict,
            'tuple': tuple, 'set': set,
        }
        py_type = type_map.get(cls_name)
        return isinstance(obj, py_type) if py_type else False

    def hx_str(obj):
        from ..interpreter import _to_str
        return _to_str(obj)

    def hx_int(obj, base=10):
        if isinstance(obj, str): return int(obj, base)
        return int(obj)

    def hx_float(obj):
        return float(obj)

    def hx_bool(obj):
        from ..interpreter import _truthy
        return _truthy(obj)

    def hx_list(obj=None):
        if obj is None: return []
        return list(obj)

    def hx_dict(*args, **kwargs):
        if args and isinstance(args[0], (list, tuple)):
            return dict(args[0])
        return dict(**kwargs)

    def hx_tuple(obj=None):
        if obj is None: return ()
        return tuple(obj)

    def hx_set(obj=None):
        if obj is None: return set()
        return set(obj)

    def hx_abs(x):
        return abs(x)

    def hx_min(*args):
        if len(args) == 1: return min(args[0])
        return min(args)

    def hx_max(*args):
        if len(args) == 1: return max(args[0])
        return max(args)

    def hx_sum(iterable, start=0):
        return sum(iterable, start)

    def hx_round(x, ndigits=None):
        return round(x, ndigits) if ndigits is not None else round(x)

    def hx_sorted(iterable, key=None, reverse=False):
        if key is not None:
            from ..interpreter import _call_value
            return sorted(iterable, key=lambda x: _call_value(key, [x], {}, 0, interp),
                          reverse=reverse)
        return sorted(iterable, reverse=reverse)

    def hx_reversed(iterable):
        return list(reversed(list(iterable)))

    def hx_enumerate(iterable, start=0):
        return list(enumerate(iterable, start))

    def hx_zip(*iterables):
        return list(zip(*iterables))

    def hx_map(func, iterable):
        from ..interpreter import _call_value
        return [_call_value(func, [x], {}, 0, interp) for x in iterable]

    def hx_filter(func, iterable):
        from ..interpreter import _call_value, _truthy
        return [x for x in iterable
                if _truthy(_call_value(func, [x], {}, 0, interp))]

    def hx_any(iterable):
        from ..interpreter import _truthy
        return any(_truthy(x) for x in iterable)

    def hx_all(iterable):
        from ..interpreter import _truthy
        return all(_truthy(x) for x in iterable)

    def hx_open(path, mode='r', encoding='utf-8'):
        return open(path, mode, encoding=encoding)

    def hx_hash(obj):
        try: return hash(obj)
        except TypeError: return id(obj)

    def hx_id(obj):
        return id(obj)

    def hx_ord(c):
        return ord(c)

    def hx_chr(n):
        return chr(n)

    def hx_hex(n):
        return hex(n)

    def hx_oct(n):
        return oct(n)

    def hx_bin(n):
        return bin(n)

    def hx_pow(base, exp, mod=None):
        return pow(base, exp, mod)

    def hx_divmod(a, b):
        return list(divmod(a, b))

    def hx_repr(obj):
        from ..interpreter import _to_str
        return repr(_to_str(obj))

    def hx_exit(code=0):
        sys.exit(code)

    def hx_assert(cond, msg="Assertion failed"):
        from ..interpreter import _truthy
        from ..errors import HaxorRuntimeError
        if not _truthy(cond):
            raise HaxorRuntimeError(str(msg))

    def hx_vars(obj=None):
        from ..interpreter import HaxorInstance
        if obj is None: return {}
        if isinstance(obj, HaxorInstance): return dict(obj.attrs)
        return {}

    def hx_dir(obj=None):
        from ..interpreter import HaxorInstance, HaxorClass
        if isinstance(obj, HaxorInstance):
            methods = list(obj.cls.methods.keys())
            attrs = list(obj.attrs.keys())
            return sorted(set(methods + attrs))
        if isinstance(obj, HaxorClass):
            return sorted(obj.methods.keys())
        return sorted(dir(obj))

    def hx_getattr(obj, name, default=None):
        from ..interpreter import HaxorInstance, HaxorAttributeError
        try:
            if isinstance(obj, HaxorInstance):
                return obj.get_attr(name)
            return getattr(obj, name)
        except (HaxorAttributeError, AttributeError):
            return default

    def hx_setattr(obj, name, value):
        from ..interpreter import HaxorInstance
        if isinstance(obj, HaxorInstance):
            obj.set_attr(name, value)
        else:
            setattr(obj, name, value)

    def hx_hasattr(obj, name):
        from ..interpreter import HaxorInstance
        if isinstance(obj, HaxorInstance):
            return name in obj.attrs or obj.cls.find_method(name) is not None
        return hasattr(obj, name)

    def hx_format(value, spec=''):
        return format(value, spec)

    def hx_iter(obj):
        return iter(obj)

    def hx_next(it, *args):
        return next(it, *args)

    def hx_callable(obj):
        from ..interpreter import HaxorFunction, BoundMethod, HaxorClass
        return isinstance(obj, (HaxorFunction, BoundMethod, HaxorClass)) or callable(obj)

    return {
        'print': hx_print,
        'input': hx_input,
        'len': hx_len,
        'range': hx_range,
        'type': hx_type,
        'isinstance': hx_isinstance,
        'str': hx_str,
        'int': hx_int,
        'float': hx_float,
        'bool': hx_bool,
        'list': hx_list,
        'dict': hx_dict,
        'tuple': hx_tuple,
        'set': hx_set,
        'abs': hx_abs,
        'min': hx_min,
        'max': hx_max,
        'sum': hx_sum,
        'round': hx_round,
        'sorted': hx_sorted,
        'reversed': hx_reversed,
        'enumerate': hx_enumerate,
        'zip': hx_zip,
        'map': hx_map,
        'filter': hx_filter,
        'any': hx_any,
        'all': hx_all,
        'open': hx_open,
        'hash': hx_hash,
        'id': hx_id,
        'ord': hx_ord,
        'chr': hx_chr,
        'hex': hx_hex,
        'oct': hx_oct,
        'bin': hx_bin,
        'pow': hx_pow,
        'divmod': hx_divmod,
        'repr': hx_repr,
        'exit': hx_exit,
        'vars': hx_vars,
        'dir': hx_dir,
        'getattr': hx_getattr,
        'setattr': hx_setattr,
        'hasattr': hx_hasattr,
        'format': hx_format,
        'iter': hx_iter,
        'next': hx_next,
        'callable': hx_callable,
        'True': True,
        'False': False,
        'None': None,
        'NotImplemented': NotImplemented,
        'Ellipsis': ...,
    }
