"""Haxor tree-walking interpreter.

Design:
- Every visit_* method receives a Node and an Environment, returns a value.
- Control flow uses _Return / _Break / _Continue exceptions (never escape to user).
- Classes are HaxorClass; instances are HaxorInstance; bound methods are BoundMethod.
- The plugin registry fires hooks at strategic points.
"""
from __future__ import annotations
import math as _math
import os
import sys
from typing import Any, List, Optional

from .ast_nodes import *
from .environment import Environment
from .errors import (
    HaxorRuntimeError, HaxorTypeError, HaxorNameError,
    HaxorAttributeError, HaxorIndexError, HaxorKeyError,
    HaxorImportError, VerificationError,
    _Return, _Break, _Continue,
)
from .plugins import registry


# ── Runtime value types ───────────────────────────────────────────────────────

class HaxorFunction:
    def __init__(self, name: str, params: list, return_type: Optional[str],
                 body: list, env: Environment, interp: 'Interpreter',
                 verify_info: Optional[dict] = None,
                 defaults: Optional[dict] = None):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body
        self.env = env
        self.interp = interp
        self.verify_info = verify_info or {}
        self.defaults = defaults or {}

    def call(self, args: list, kwargs: dict = None, *, line: int = 0) -> Any:
        kwargs = kwargs or {}
        env = self.env.child()
        # Bind positional args, keyword args, then defaults
        for i, (pname, _ann) in enumerate(self.params):
            if i < len(args):
                env.define(pname, args[i])
            elif pname in kwargs:
                env.define(pname, kwargs[pname])
            elif pname in self.defaults:
                env.define(pname, self.defaults[pname])
            else:
                raise HaxorRuntimeError(
                    f"'{self.name}' missing argument '{pname}'", line)

        # Pre-condition check
        if 'pre' in self.verify_info:
            result = self._eval_condition(self.verify_info['pre'], env, line)
            if result is False:
                raise VerificationError(
                    f"Precondition failed for '{self.name}': {self.verify_info['pre']}",
                    line)

        try:
            for stmt in self.body:
                self.interp.visit(stmt, env)
            ret_val = None
        except _Return as r:
            ret_val = r.value

        # Post-condition check
        if 'post' in self.verify_info:
            post_env = env.child()
            post_env.define('result', ret_val)
            result = self._eval_condition(self.verify_info['post'], post_env, line)
            if result is False:
                raise VerificationError(
                    f"Postcondition failed for '{self.name}': {self.verify_info['post']}",
                    line)
        return ret_val

    def _eval_condition(self, cond_src: str, env: Environment, line: int) -> Any:
        from .lexer import Lexer
        from .parser import Parser
        try:
            tokens = Lexer(cond_src).tokenize()
            node = Parser(tokens).parse_expression()
            return self.interp.visit(node, env)
        except Exception as e:
            raise VerificationError(f"Error evaluating condition {cond_src!r}: {e}", line)

    def __repr__(self) -> str:
        return f"<fn {self.name}>"


class HaxorClass:
    def __init__(self, name: str, bases: list, methods: dict,
                 class_env: Environment, interp: 'Interpreter'):
        self.name = name
        self.bases = bases
        self.methods = methods
        self.class_env = class_env
        self.interp = interp

    def find_method(self, name: str) -> Optional[HaxorFunction]:
        if name in self.methods:
            return self.methods[name]
        for base in self.bases:
            if isinstance(base, HaxorClass):
                m = base.find_method(name)
                if m is not None:
                    return m
        return None

    def __call__(self, args: list, kwargs: dict = None, line: int = 0) -> 'HaxorInstance':
        instance = HaxorInstance(self)
        init = self.find_method('init')
        if init is not None:
            init.call([instance] + args, kwargs, line=line)
        return instance

    def __repr__(self) -> str:
        return f"<class {self.name}>"


class HaxorInstance:
    def __init__(self, cls: HaxorClass):
        self.cls = cls
        self.attrs: dict = {}

    def get_attr(self, name: str, line: int = 0) -> Any:
        if name in self.attrs:
            return self.attrs[name]
        method = self.cls.find_method(name)
        if method is not None:
            return BoundMethod(method, self)
        raise HaxorAttributeError(
            f"'{self.cls.name}' object has no attribute '{name}'", line)

    def set_attr(self, name: str, value: Any) -> None:
        self.attrs[name] = value

    def __repr__(self) -> str:
        return f"<{self.cls.name} object>"


class BoundMethod:
    def __init__(self, fn: HaxorFunction, instance: HaxorInstance):
        self.fn = fn
        self.instance = instance

    def call(self, args: list, kwargs: dict = None, line: int = 0) -> Any:
        return self.fn.call([self.instance] + args, kwargs, line=line)

    def __repr__(self) -> str:
        return f"<bound method {self.fn.name}>"


class HaxorModule:
    def __init__(self, name: str, env: Environment):
        self.name = name
        self.env = env

    def get_attr(self, name: str, line: int = 0) -> Any:
        return self.env.get(name, line)

    def __repr__(self) -> str:
        return f"<module {self.name!r}>"


# ── Interpreter ───────────────────────────────────────────────────────────────

class Interpreter:
    def __init__(self, stdlib_path: Optional[str] = None):
        self.global_env = Environment()
        self._stdlib_path = stdlib_path
        self._module_cache: dict[str, HaxorModule] = {}
        self._setup_builtins()

    # ── Visitor dispatch ──────────────────────────────────────────────────────

    def visit(self, node: Node, env: Optional[Environment] = None) -> Any:
        if env is None:
            env = self.global_env
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is None:
            raise HaxorRuntimeError(
                f"No visitor for node type {type(node).__name__}", node.line)
        return method(node, env)

    def execute(self, source: str) -> Any:
        from .lexer import Lexer
        from .parser import Parser
        tokens = Lexer(source).tokenize()
        registry.trigger('post_lex', tokens)
        tree = Parser(tokens).parse()
        registry.trigger('post_parse', tree)
        result = self.visit(tree, self.global_env)
        registry.trigger('post_execute', result)
        return result

    # ── Statement visitors ────────────────────────────────────────────────────

    def visit_Program(self, node: Program, env: Environment) -> Any:
        result = None
        for stmt in node.body:
            result = self.visit(stmt, env)
        return result

    def visit_LetStmt(self, node: LetStmt, env: Environment) -> None:
        val = self.visit(node.value, env) if node.value is not None else None
        env.define(node.name, val)

    def visit_FnDef(self, node: FnDef, env: Environment) -> HaxorFunction:
        verify_info = {}
        for dec in node.decorators:
            if isinstance(dec, VerifyDecorator):
                if dec.pre:
                    verify_info['pre'] = dec.pre
                if dec.post:
                    verify_info['post'] = dec.post
                if dec.invariant:
                    verify_info['invariant'] = dec.invariant
        # Evaluate default values eagerly in the definition scope
        evaluated_defaults = {
            pname: self.visit(expr, env)
            for pname, expr in node.defaults.items()
        }
        fn = HaxorFunction(
            name=node.name, params=node.params, return_type=node.return_type,
            body=node.body, env=env, interp=self,
            verify_info=verify_info or None,
            defaults=evaluated_defaults,
        )
        if node.name != '<lambda>':
            env.define(node.name, fn)
        # Apply non-verify decorators
        for dec in reversed(node.decorators):
            if not isinstance(dec, VerifyDecorator):
                decorator = self.visit(dec, env)
                fn = _call_value(decorator, [fn], {}, node.line, self)
        if node.name != '<lambda>':
            env.define(node.name, fn)
        return fn

    def visit_ClassDef(self, node: ClassDef, env: Environment) -> HaxorClass:
        bases = []
        for base_name in node.bases:
            base = env.get(base_name, node.line)
            if not isinstance(base, HaxorClass):
                raise HaxorTypeError(f"Base class '{base_name}' is not a class", node.line)
            bases.append(base)
        class_env = env.child()
        methods: dict = {}
        for stmt in node.body:
            if isinstance(stmt, FnDef):
                fn = self.visit_FnDef(stmt, class_env)
                methods[stmt.name] = fn
            elif isinstance(stmt, PassStmt):
                pass
            elif isinstance(stmt, LetStmt):
                self.visit_LetStmt(stmt, class_env)
            else:
                self.visit(stmt, class_env)
        cls = HaxorClass(name=node.name, bases=bases, methods=methods,
                         class_env=class_env, interp=self)
        env.define(node.name, cls)
        return cls

    def visit_IfStmt(self, node: IfStmt, env: Environment) -> None:
        if _truthy(self.visit(node.condition, env)):
            self._exec_block(node.then_body, env.child())
        else:
            for ec, eb in node.elif_clauses:
                if _truthy(self.visit(ec, env)):
                    self._exec_block(eb, env.child())
                    return
            if node.else_body is not None:
                self._exec_block(node.else_body, env.child())

    def visit_ForStmt(self, node: ForStmt, env: Environment) -> None:
        iterable = self.visit(node.iterable, env)
        try:
            it = iter(iterable)
        except TypeError:
            raise HaxorTypeError("Object is not iterable", node.line)
        loop_env = env.child()
        try:
            for item in it:
                loop_env.define(node.target, item)
                try:
                    self._exec_block(node.body, loop_env.child())
                except _Continue:
                    continue
        except _Break:
            pass

    def visit_WhileStmt(self, node: WhileStmt, env: Environment) -> None:
        loop_env = env.child()
        try:
            while _truthy(self.visit(node.condition, env)):
                try:
                    self._exec_block(node.body, loop_env.child())
                except _Continue:
                    continue
        except _Break:
            pass

    def visit_ReturnStmt(self, node: ReturnStmt, env: Environment) -> None:
        val = self.visit(node.value, env) if node.value is not None else None
        raise _Return(val)

    def visit_BreakStmt(self, node: BreakStmt, env: Environment) -> None:
        raise _Break()

    def visit_ContinueStmt(self, node: ContinueStmt, env: Environment) -> None:
        raise _Continue()

    def visit_PassStmt(self, node: PassStmt, env: Environment) -> None:
        pass

    def visit_ImportStmt(self, node: ImportStmt, env: Environment) -> None:
        if node.from_module:
            mod = self._import_module(node.from_module, node.line)
            for name, alias in node.names:
                if name == '*':
                    for k, v in mod.env.snapshot().items():
                        env.define(k, v)
                else:
                    val = mod.get_attr(name, node.line)
                    env.define(alias or name, val)
        else:
            mod = self._import_module(node.module, node.line)
            top = node.module.split('.')[0]
            env.define(top, mod)

    def visit_AssertStmt(self, node: AssertStmt, env: Environment) -> None:
        if not _truthy(self.visit(node.condition, env)):
            msg = self.visit(node.message, env) if node.message else "Assertion failed"
            raise HaxorRuntimeError(str(msg), node.line)

    def visit_ExprStmt(self, node: ExprStmt, env: Environment) -> Any:
        return self.visit(node.expr, env)

    # ── Expression visitors ───────────────────────────────────────────────────

    def visit_Assign(self, node: Assign, env: Environment) -> Any:
        rhs = self.visit(node.value, env)
        if node.op:
            lhs = self.visit(node.target, env)
            rhs = _binop(lhs, node.op, rhs, node.line)
        self._assign_target(node.target, rhs, env, node.line)
        return rhs

    def _assign_target(self, target: Node, value: Any, env: Environment, line: int) -> None:
        if isinstance(target, Name):
            env.assign(target.id, value, line)
        elif isinstance(target, Attribute):
            obj = self.visit(target.obj, env)
            if isinstance(obj, HaxorInstance):
                obj.set_attr(target.attr, value)
            elif isinstance(obj, HaxorModule):
                obj.env.define(target.attr, value)
            else:
                raise HaxorAttributeError(
                    f"Cannot set attribute on {type(obj).__name__}", line)
        elif isinstance(target, Subscript):
            obj = self.visit(target.obj, env)
            if isinstance(target.index, Slice):
                sl = self._eval_slice(target.index, env)
                try:
                    obj[sl] = value
                except TypeError as e:
                    raise HaxorRuntimeError(str(e), line)
            else:
                idx = self.visit(target.index, env)
                try:
                    obj[idx] = value
                except (TypeError, KeyError, IndexError) as e:
                    raise HaxorRuntimeError(str(e), line)
        else:
            raise HaxorRuntimeError("Invalid assignment target", line)

    def visit_BinOp(self, node: BinOp, env: Environment) -> Any:
        left = self.visit(node.left, env)
        right = self.visit(node.right, env)
        return _binop(left, node.op, right, node.line)

    def visit_UnaryOp(self, node: UnaryOp, env: Environment) -> Any:
        val = self.visit(node.operand, env)
        try:
            if node.op == '-': return -val
            if node.op == '+': return +val
            if node.op == '~': return ~val
            if node.op == 'not': return not _truthy(val)
        except TypeError as e:
            raise HaxorTypeError(str(e), node.line)

    def visit_BoolOp(self, node: BoolOp, env: Environment) -> Any:
        if node.op == 'and':
            result = self.visit(node.values[0], env)
            for val_node in node.values[1:]:
                if not _truthy(result):
                    return result
                result = self.visit(val_node, env)
            return result
        else:  # or
            result = self.visit(node.values[0], env)
            for val_node in node.values[1:]:
                if _truthy(result):
                    return result
                result = self.visit(val_node, env)
            return result

    def visit_Compare(self, node: Compare, env: Environment) -> bool:
        left = self.visit(node.left, env)
        for op, comparator_node in zip(node.ops, node.comparators):
            right = self.visit(comparator_node, env)
            if not _compare(left, op, right, node.line):
                return False
            left = right
        return True

    def visit_Call(self, node: Call, env: Environment) -> Any:
        func = self.visit(node.func, env)
        args = [self.visit(a, env) for a in node.args]
        kwargs = {k: self.visit(v, env) for k, v in node.kwargs}
        return _call_value(func, args, kwargs, node.line, self)

    def visit_Attribute(self, node: Attribute, env: Environment) -> Any:
        obj = self.visit(node.obj, env)
        if isinstance(obj, HaxorInstance):
            return obj.get_attr(node.attr, node.line)
        if isinstance(obj, HaxorClass):
            method = obj.find_method(node.attr)
            if method is not None:
                return method
            raise HaxorAttributeError(
                f"Class '{obj.name}' has no attribute '{node.attr}'", node.line)
        if isinstance(obj, HaxorModule):
            return obj.get_attr(node.attr, node.line)
        # Fall back to Python attribute access (for stdlib objects)
        try:
            return getattr(obj, node.attr)
        except AttributeError:
            raise HaxorAttributeError(
                f"'{type(obj).__name__}' has no attribute '{node.attr}'", node.line)

    def _eval_slice(self, node: Slice, env: Environment) -> slice:
        start = self.visit(node.start, env) if node.start is not None else None
        stop  = self.visit(node.stop,  env) if node.stop  is not None else None
        step  = self.visit(node.step,  env) if node.step  is not None else None
        return slice(start, stop, step)

    def visit_Subscript(self, node: Subscript, env: Environment) -> Any:
        obj = self.visit(node.obj, env)
        if isinstance(node.index, Slice):
            sl = self._eval_slice(node.index, env)
            try:
                return obj[sl]
            except TypeError as e:
                raise HaxorTypeError(str(e), node.line)
        idx = self.visit(node.index, env)
        try:
            return obj[idx]
        except (IndexError, KeyError) as e:
            raise (HaxorIndexError if isinstance(e, IndexError) else HaxorKeyError)(
                str(e), node.line)
        except TypeError as e:
            raise HaxorTypeError(str(e), node.line)

    def visit_Name(self, node: Name, env: Environment) -> Any:
        return env.get(node.id, node.line)

    def visit_Literal(self, node: Literal, env: Environment) -> Any:
        return node.value

    def visit_ListExpr(self, node: ListExpr, env: Environment) -> list:
        return [self.visit(e, env) for e in node.elements]

    def visit_DictExpr(self, node: DictExpr, env: Environment) -> dict:
        return {self.visit(k, env): self.visit(v, env)
                for k, v in zip(node.keys, node.values)}

    def visit_TupleExpr(self, node: TupleExpr, env: Environment) -> tuple:
        return tuple(self.visit(e, env) for e in node.elements)

    def visit_SetExpr(self, node: SetExpr, env: Environment) -> set:
        return {self.visit(e, env) for e in node.elements}

    def visit_FStringExpr(self, node: FStringExpr, env: Environment) -> str:
        parts = []
        for part in node.parts:
            if isinstance(part, FStringLiteral):
                parts.append(part.value)
            else:
                parts.append(_to_str(self.visit(part, env)))
        return ''.join(parts)

    def visit_LambdaExpr(self, node: LambdaExpr, env: Environment) -> HaxorFunction:
        params = [(p, None) for p in node.params]
        body = [ReturnStmt(value=node.body, line=node.line, col=node.col)]
        return HaxorFunction('<lambda>', params, None, body, env, self)

    def visit_FnDef_anon(self, node: FnDef, env: Environment) -> HaxorFunction:
        # FnDef with name='<lambda>' — anonymous function expression
        return self.visit_FnDef(node, env)

    def visit_IfExpr(self, node: IfExpr, env: Environment) -> Any:
        if _truthy(self.visit(node.condition, env)):
            return self.visit(node.then_val, env)
        return self.visit(node.else_val, env)

    def visit_ListComp(self, node: ListComp, env: Environment) -> list:
        iterable = self.visit(node.iterable, env)
        result = []
        comp_env = env.child()
        for item in iterable:
            comp_env.define(node.target, item)
            if node.condition is None or _truthy(self.visit(node.condition, comp_env)):
                result.append(self.visit(node.element, comp_env))
        return result

    def visit_VerifyDecorator(self, node: VerifyDecorator, env: Environment) -> VerifyDecorator:
        return node  # handled in visit_FnDef

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _exec_block(self, body: list, env: Environment) -> None:
        for stmt in body:
            self.visit(stmt, env)

    def _import_module(self, name: str, line: int) -> HaxorModule:
        if name in self._module_cache:
            return self._module_cache[name]

        # Plugin-provided modules
        plugin_mod = registry.get_module(name)
        if plugin_mod is not None:
            self._module_cache[name] = plugin_mod
            return plugin_mod

        # Try stdlib Python-side modules
        stdlib_mod = _load_stdlib_module(name, self)
        if stdlib_mod is not None:
            self._module_cache[name] = stdlib_mod
            return stdlib_mod

        # Try .hx file on disk
        search_dirs = [
            os.path.join(os.path.dirname(__file__), '..', 'stdlib'),
        ]
        if self._stdlib_path:
            search_dirs.insert(0, self._stdlib_path)

        parts = name.split('.')
        for d in search_dirs:
            path = os.path.join(d, *parts) + '.hx'
            if os.path.exists(path):
                with open(path) as f:
                    source = f.read()
                mod_env = self.global_env.child()
                from .lexer import Lexer
                from .parser import Parser
                tokens = Lexer(source).tokenize()
                tree = Parser(tokens).parse()
                Interpreter._exec_in(self, tree, mod_env)
                mod = HaxorModule(name, mod_env)
                self._module_cache[name] = mod
                return mod

        raise HaxorImportError(f"Module '{name}' not found", line)

    @staticmethod
    def _exec_in(interp: 'Interpreter', tree: Program, env: Environment) -> None:
        for stmt in tree.body:
            interp.visit(stmt, env)

    # ── Built-in setup ────────────────────────────────────────────────────────

    def _setup_builtins(self) -> None:
        from .stdlib._builtins import get_builtins
        for name, fn in get_builtins(self).items():
            self.global_env.define(name, fn)
        # Merge plugin builtins
        for name, fn in registry.get_builtins().items():
            self.global_env.define(name, fn)


# ── Pure helpers (no interpreter state) ──────────────────────────────────────

def _truthy(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (int, float)) and value == 0:
        return False
    if isinstance(value, (str, list, dict, tuple, set)) and len(value) == 0:
        return False
    return True


def _to_str(value: Any) -> str:
    if value is None:
        return 'None'
    if value is True:
        return 'True'
    if value is False:
        return 'False'
    if isinstance(value, (HaxorInstance, HaxorClass, HaxorFunction, BoundMethod)):
        return repr(value)
    return str(value)


def _binop(left: Any, op: str, right: Any, line: int) -> Any:  # noqa: C901
    try:
        if op == '+':
            return left + right
        if op == '-':
            return left - right
        if op == '*':
            return left * right
        if op == '/':
            if right == 0:
                raise HaxorRuntimeError("Division by zero", line)
            return left / right
        if op == '//':
            if right == 0:
                raise HaxorRuntimeError("Division by zero", line)
            return left // right
        if op == '%':
            if right == 0:
                raise HaxorRuntimeError("Modulo by zero", line)
            return left % right
        if op == '**':
            return left ** right
        if op == '|': return left | right
        if op == '&': return left & right
        if op == '^': return left ^ right
        if op == '<<': return left << right
        if op == '>>': return left >> right
        if op == '@':
            # Matrix multiply — delegate to Python
            return left @ right
    except (TypeError, ValueError) as e:
        raise HaxorTypeError(str(e), line)
    raise HaxorRuntimeError(f"Unknown operator '{op}'", line)


def _compare(left: Any, op: str, right: Any, line: int) -> bool:
    try:
        if op == '==':  return left == right
        if op == '!=':  return left != right
        if op == '<':   return left < right
        if op == '>':   return left > right
        if op == '<=':  return left <= right
        if op == '>=':  return left >= right
        if op == 'in':  return left in right
        if op == 'not in': return left not in right
        if op == 'is':     return left is right
        if op == 'is not': return left is not right
    except TypeError as e:
        raise HaxorTypeError(str(e), line)
    raise HaxorRuntimeError(f"Unknown comparison '{op}'", line)


def _call_value(func: Any, args: list, kwargs: dict, line: int,
                interp: 'Interpreter') -> Any:
    if isinstance(func, HaxorFunction):
        return func.call(args, kwargs, line=line)
    if isinstance(func, BoundMethod):
        return func.call(args, kwargs, line=line)
    if isinstance(func, HaxorClass):
        return func(args, kwargs, line=line)
    if callable(func):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise HaxorRuntimeError(str(e), line)
    raise HaxorTypeError(f"'{type(func).__name__}' is not callable", line)


def _load_stdlib_module(name: str, interp: 'Interpreter') -> Optional[HaxorModule]:
    """Load a Python-implemented stdlib module by dotted name."""
    from . import stdlib as _stdlib_pkg
    loaders = getattr(_stdlib_pkg, '_MODULE_LOADERS', {})
    loader = loaders.get(name)
    if loader is None:
        return None
    mod_env = interp.global_env.child()
    loader(mod_env, interp)
    return HaxorModule(name, mod_env)
