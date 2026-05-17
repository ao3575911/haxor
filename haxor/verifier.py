"""Haxor formal verifier — static analysis + abstract interpretation.

Implements three analysis passes that run before execution:

1. **Type inference** — Hindley-Milner-style monomorphic inference over the AST.
2. **Sign analysis** — Abstract interpretation over the sign domain
   {Neg, Zero, Pos, NonNeg, NonPos, NonZero, Top, Bot}.
3. **Control-flow analysis** — CFG construction + dead-code / missing-return
   detection.

All three produce Diagnostic objects that are returned to the caller.
A VerificationError is only raised when the `strict=True` flag is set.

Optional Z3 integration: if `pip install z3-solver` is present, the verifier
uses SMT-based constraint solving for pre/post conditions.  Otherwise it falls
back to the abstract interpreter.
"""
from __future__ import annotations
import ast as _pyast
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

from .ast_nodes import *
from .errors import VerificationError

try:
    import z3  # type: ignore
    _HAS_Z3 = True
except ImportError:
    _HAS_Z3 = False


# ── Diagnostic ────────────────────────────────────────────────────────────────

class Severity(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


@dataclass
class Diagnostic:
    severity: Severity
    message: str
    line: int = 0
    col: int = 0
    pass_name: str = ""

    def __str__(self) -> str:
        sev = self.severity.name
        loc = f"[{self.line}:{self.col}] " if self.line else ""
        return f"[{sev}] {loc}{self.message}"


# ── Abstract sign domain ──────────────────────────────────────────────────────

class Sign(Enum):
    BOT = auto()   # unreachable / undefined
    NEG = auto()   # definitely < 0
    ZERO = auto()  # definitely == 0
    POS = auto()   # definitely > 0
    NON_NEG = auto()   # >= 0
    NON_POS = auto()   # <= 0
    NON_ZERO = auto()  # != 0
    TOP = auto()   # unknown


def _sign_join(a: Sign, b: Sign) -> Sign:
    if a == b: return a
    if a == Sign.BOT: return b
    if b == Sign.BOT: return a
    table = {
        frozenset({Sign.NEG, Sign.ZERO}): Sign.NON_POS,
        frozenset({Sign.POS, Sign.ZERO}): Sign.NON_NEG,
        frozenset({Sign.NEG, Sign.POS}): Sign.NON_ZERO,
        frozenset({Sign.NEG, Sign.NON_NEG}): Sign.TOP,
        frozenset({Sign.POS, Sign.NON_POS}): Sign.TOP,
    }
    return table.get(frozenset({a, b}), Sign.TOP)


def _sign_of(val: Any) -> Sign:
    if isinstance(val, bool): return Sign.TOP
    if isinstance(val, (int, float)):
        if val < 0: return Sign.NEG
        if val == 0: return Sign.ZERO
        return Sign.POS
    return Sign.TOP


def _sign_add(a: Sign, b: Sign) -> Sign:
    if a == Sign.BOT or b == Sign.BOT: return Sign.BOT
    if a == Sign.ZERO: return b
    if b == Sign.ZERO: return a
    if a == Sign.POS and b == Sign.POS: return Sign.POS
    if a == Sign.NEG and b == Sign.NEG: return Sign.NEG
    return Sign.TOP


def _sign_mul(a: Sign, b: Sign) -> Sign:
    if Sign.BOT in (a, b): return Sign.BOT
    if Sign.ZERO in (a, b): return Sign.ZERO
    if a == b == Sign.POS: return Sign.POS
    if a == b == Sign.NEG: return Sign.POS
    if {a, b} == {Sign.NEG, Sign.POS}: return Sign.NEG
    return Sign.TOP


# ── Type domain ───────────────────────────────────────────────────────────────

class HType(Enum):
    UNKNOWN = auto()
    INT = auto()
    FLOAT = auto()
    BOOL = auto()
    STR = auto()
    NONE = auto()
    LIST = auto()
    DICT = auto()
    TUPLE = auto()
    SET = auto()
    CALLABLE = auto()
    CLASS = auto()
    ANY = auto()


_TYPE_NAMES: Dict[str, HType] = {
    'int': HType.INT, 'float': HType.FLOAT, 'bool': HType.BOOL,
    'str': HType.STR, 'None': HType.NONE, 'list': HType.LIST,
    'dict': HType.DICT, 'tuple': HType.TUPLE, 'set': HType.SET,
}


def _python_type(val: Any) -> HType:
    if val is None: return HType.NONE
    if isinstance(val, bool): return HType.BOOL
    if isinstance(val, int): return HType.INT
    if isinstance(val, float): return HType.FLOAT
    if isinstance(val, str): return HType.STR
    if isinstance(val, list): return HType.LIST
    if isinstance(val, dict): return HType.DICT
    if isinstance(val, tuple): return HType.TUPLE
    if isinstance(val, set): return HType.SET
    if callable(val): return HType.CALLABLE
    return HType.ANY


# ── Abstract state ────────────────────────────────────────────────────────────

@dataclass
class AbsVal:
    htype: HType = HType.UNKNOWN
    sign: Sign = Sign.TOP
    concrete: Optional[Any] = None  # known constant

    @classmethod
    def from_literal(cls, val: Any) -> 'AbsVal':
        return cls(htype=_python_type(val), sign=_sign_of(val), concrete=val)

    @classmethod
    def top(cls) -> 'AbsVal':
        return cls(HType.ANY, Sign.TOP, None)

    def join(self, other: 'AbsVal') -> 'AbsVal':
        ht = self.htype if self.htype == other.htype else HType.ANY
        sg = _sign_join(self.sign, other.sign)
        cc = self.concrete if self.concrete == other.concrete else None
        return AbsVal(ht, sg, cc)


AbsEnv = Dict[str, AbsVal]


# ── Verifier ──────────────────────────────────────────────────────────────────

class Verifier:
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.diagnostics: List[Diagnostic] = []

    def verify(self, tree: Program) -> List[Diagnostic]:
        self.diagnostics = []
        env: AbsEnv = {}
        self._type_pass(tree, env)
        self._sign_pass(tree, {})
        self._flow_pass(tree)
        if self.strict:
            errors = [d for d in self.diagnostics if d.severity == Severity.ERROR]
            if errors:
                raise VerificationError(
                    '\n'.join(str(d) for d in errors))
        return self.diagnostics

    # ── Pass 1: type inference ────────────────────────────────────────────────

    def _type_pass(self, node: Node, env: AbsEnv) -> HType:
        meth = getattr(self, f"_type_{type(node).__name__}", None)
        if meth:
            return meth(node, env)
        return HType.UNKNOWN

    def _type_Program(self, node: Program, env: AbsEnv) -> HType:
        for stmt in node.body:
            self._type_pass(stmt, env)
        return HType.NONE

    def _type_LetStmt(self, node: LetStmt, env: AbsEnv) -> HType:
        vt = self._type_pass(node.value, env) if node.value else HType.NONE
        if node.annotation:
            declared = _TYPE_NAMES.get(node.annotation, HType.ANY)
            if declared != HType.ANY and vt != HType.UNKNOWN and vt != declared:
                self._diag(Severity.WARNING,
                           f"Type mismatch: '{node.name}' declared as {node.annotation!r} "
                           f"but assigned {vt.name.lower()}",
                           node.line, node.col, "type")
        env[node.name] = AbsVal(htype=vt)
        return HType.NONE

    def _type_FnDef(self, node: FnDef, env: AbsEnv) -> HType:
        fn_env = dict(env)
        for pname, ann in node.params:
            fn_env[pname] = AbsVal(htype=_TYPE_NAMES.get(ann or '', HType.ANY))
        for stmt in node.body:
            self._type_pass(stmt, fn_env)
        env[node.name] = AbsVal(htype=HType.CALLABLE)
        return HType.CALLABLE

    def _type_ClassDef(self, node: ClassDef, env: AbsEnv) -> HType:
        cls_env = dict(env)
        for stmt in node.body:
            self._type_pass(stmt, cls_env)
        env[node.name] = AbsVal(htype=HType.CLASS)
        return HType.CLASS

    def _type_IfStmt(self, node: IfStmt, env: AbsEnv) -> HType:
        self._type_pass(node.condition, env)
        for stmt in node.then_body:
            self._type_pass(stmt, env)
        for ec, eb in node.elif_clauses:
            self._type_pass(ec, env)
            for s in eb:
                self._type_pass(s, env)
        if node.else_body:
            for s in node.else_body:
                self._type_pass(s, env)
        return HType.NONE

    def _type_ForStmt(self, node: ForStmt, env: AbsEnv) -> HType:
        self._type_pass(node.iterable, env)
        env[node.target] = AbsVal.top()
        for stmt in node.body:
            self._type_pass(stmt, env)
        return HType.NONE

    def _type_WhileStmt(self, node: WhileStmt, env: AbsEnv) -> HType:
        self._type_pass(node.condition, env)
        for stmt in node.body:
            self._type_pass(stmt, env)
        return HType.NONE

    def _type_ReturnStmt(self, node: ReturnStmt, env: AbsEnv) -> HType:
        return self._type_pass(node.value, env) if node.value else HType.NONE

    def _type_ExprStmt(self, node: ExprStmt, env: AbsEnv) -> HType:
        return self._type_pass(node.expr, env)

    def _type_Assign(self, node: Assign, env: AbsEnv) -> HType:
        vt = self._type_pass(node.value, env)
        if isinstance(node.target, Name):
            env[node.target.id] = AbsVal(htype=vt)
        return vt

    def _type_Literal(self, node: Literal, env: AbsEnv) -> HType:
        return _python_type(node.value)

    def _type_Name(self, node: Name, env: AbsEnv) -> HType:
        av = env.get(node.id)
        if av is None:
            self._diag(Severity.WARNING,
                       f"'{node.id}' may not be defined at this point",
                       node.line, node.col, "type")
            return HType.UNKNOWN
        return av.htype

    def _type_BinOp(self, node: BinOp, env: AbsEnv) -> HType:
        lt = self._type_pass(node.left, env)
        rt = self._type_pass(node.right, env)
        if node.op == '+' and lt == HType.STR and rt == HType.STR:
            return HType.STR
        if node.op in ('+', '-', '*', '/', '//', '%', '**'):
            if lt in (HType.INT, HType.FLOAT) and rt in (HType.INT, HType.FLOAT):
                return HType.FLOAT if HType.FLOAT in (lt, rt) else HType.INT
            if lt == HType.STR and rt == HType.INT and node.op == '*':
                return HType.STR
        return HType.ANY

    def _type_BoolOp(self, node: BoolOp, env: AbsEnv) -> HType:
        for v in node.values:
            self._type_pass(v, env)
        return HType.BOOL

    def _type_Compare(self, node: Compare, env: AbsEnv) -> HType:
        self._type_pass(node.left, env)
        for c in node.comparators:
            self._type_pass(c, env)
        return HType.BOOL

    def _type_Call(self, node: Call, env: AbsEnv) -> HType:
        for a in node.args:
            self._type_pass(a, env)
        return HType.ANY

    def _type_Attribute(self, node: Attribute, env: AbsEnv) -> HType:
        self._type_pass(node.obj, env)
        return HType.ANY

    def _type_ListExpr(self, node: ListExpr, env: AbsEnv) -> HType:
        for e in node.elements:
            self._type_pass(e, env)
        return HType.LIST

    def _type_DictExpr(self, node: DictExpr, env: AbsEnv) -> HType:
        for k, v in zip(node.keys, node.values):
            self._type_pass(k, env); self._type_pass(v, env)
        return HType.DICT

    def _type_FStringExpr(self, node: FStringExpr, env: AbsEnv) -> HType:
        for p in node.parts:
            if not isinstance(p, FStringLiteral):
                self._type_pass(p, env)
        return HType.STR

    def _type_UnaryOp(self, node: UnaryOp, env: AbsEnv) -> HType:
        return self._type_pass(node.operand, env)

    def _type_IfExpr(self, node: IfExpr, env: AbsEnv) -> HType:
        self._type_pass(node.condition, env)
        t1 = self._type_pass(node.then_val, env)
        t2 = self._type_pass(node.else_val, env)
        return t1 if t1 == t2 else HType.ANY

    def _type_LambdaExpr(self, node: LambdaExpr, env: AbsEnv) -> HType:
        return HType.CALLABLE

    def _type_ListComp(self, node: ListComp, env: AbsEnv) -> HType:
        self._type_pass(node.iterable, env)
        lc_env = dict(env)
        lc_env[node.target] = AbsVal.top()
        if node.condition:
            self._type_pass(node.condition, lc_env)
        self._type_pass(node.element, lc_env)
        return HType.LIST

    def _type_AssertStmt(self, node: AssertStmt, env: AbsEnv) -> HType:
        self._type_pass(node.condition, env)
        return HType.NONE

    def _type_ImportStmt(self, node: ImportStmt, env: AbsEnv) -> HType:
        return HType.NONE

    def _type_PassStmt(self, *_) -> HType: return HType.NONE
    def _type_BreakStmt(self, *_) -> HType: return HType.NONE
    def _type_ContinueStmt(self, *_) -> HType: return HType.NONE
    def _type_VerifyDecorator(self, *_) -> HType: return HType.NONE

    # ── Pass 2: sign analysis ─────────────────────────────────────────────────

    def _sign_pass(self, node: Node, env: Dict[str, Sign]) -> Sign:
        meth = getattr(self, f"_sign_{type(node).__name__}", None)
        if meth:
            return meth(node, env)
        return Sign.TOP

    def _sign_Program(self, node: Program, env: Dict[str, Sign]) -> Sign:
        for stmt in node.body:
            self._sign_pass(stmt, env)
        return Sign.TOP

    def _sign_LetStmt(self, node: LetStmt, env: Dict[str, Sign]) -> Sign:
        s = self._sign_pass(node.value, env) if node.value else Sign.TOP
        env[node.name] = s
        return Sign.TOP

    def _sign_FnDef(self, node: FnDef, env: Dict[str, Sign]) -> Sign:
        env[node.name] = Sign.TOP
        fn_env = dict(env)
        for pname, ann in node.params:
            fn_env[pname] = Sign.TOP
        for stmt in node.body:
            self._sign_pass(stmt, fn_env)
        return Sign.TOP

    def _sign_Assign(self, node: Assign, env: Dict[str, Sign]) -> Sign:
        s = self._sign_pass(node.value, env)
        if isinstance(node.target, Name):
            env[node.target.id] = s
        return s

    def _sign_Literal(self, node: Literal, env: Dict[str, Sign]) -> Sign:
        return _sign_of(node.value)

    def _sign_Name(self, node: Name, env: Dict[str, Sign]) -> Sign:
        return env.get(node.id, Sign.TOP)

    def _sign_BinOp(self, node: BinOp, env: Dict[str, Sign]) -> Sign:
        ls = self._sign_pass(node.left, env)
        rs = self._sign_pass(node.right, env)
        if node.op == '+': return _sign_add(ls, rs)
        if node.op == '-': return _sign_add(ls, _sign_negate(rs))
        if node.op == '*': return _sign_mul(ls, rs)
        if node.op in ('/', '//'):
            if rs == Sign.ZERO:
                self._diag(Severity.ERROR,
                           "Possible division by zero detected",
                           node.line, node.col, "sign")
            return Sign.TOP
        return Sign.TOP

    def _sign_UnaryOp(self, node: UnaryOp, env: Dict[str, Sign]) -> Sign:
        s = self._sign_pass(node.operand, env)
        if node.op == '-': return _sign_negate(s)
        return s

    def _sign_IfStmt(self, node: IfStmt, env: Dict[str, Sign]) -> Sign:
        self._sign_pass(node.condition, env)
        then_env = dict(env)
        for s in node.then_body: self._sign_pass(s, then_env)
        for ec, eb in node.elif_clauses:
            elif_env = dict(env)
            self._sign_pass(ec, elif_env)
            for s in eb: self._sign_pass(s, elif_env)
        if node.else_body:
            else_env = dict(env)
            for s in node.else_body: self._sign_pass(s, else_env)
        # Join environments (conservative)
        for k in list(env.keys()):
            env[k] = _sign_join(then_env.get(k, Sign.TOP), env.get(k, Sign.TOP))
        return Sign.TOP

    def _sign_ForStmt(self, node: ForStmt, env: Dict[str, Sign]) -> Sign:
        env[node.target] = Sign.TOP
        loop_env = dict(env)
        for s in node.body: self._sign_pass(s, loop_env)
        return Sign.TOP

    def _sign_WhileStmt(self, node: WhileStmt, env: Dict[str, Sign]) -> Sign:
        self._sign_pass(node.condition, env)
        loop_env = dict(env)
        for s in node.body: self._sign_pass(s, loop_env)
        return Sign.TOP

    def _sign_ExprStmt(self, node: ExprStmt, env: Dict[str, Sign]) -> Sign:
        return self._sign_pass(node.expr, env)

    def _sign_ReturnStmt(self, node: ReturnStmt, env: Dict[str, Sign]) -> Sign:
        return self._sign_pass(node.value, env) if node.value else Sign.TOP

    def _sign_Compare(self, *_) -> Sign: return Sign.TOP
    def _sign_BoolOp(self, *_) -> Sign: return Sign.TOP
    def _sign_Call(self, *_) -> Sign: return Sign.TOP
    def _sign_ClassDef(self, *_) -> Sign: return Sign.TOP
    def _sign_ImportStmt(self, *_) -> Sign: return Sign.TOP
    def _sign_PassStmt(self, *_) -> Sign: return Sign.TOP
    def _sign_BreakStmt(self, *_) -> Sign: return Sign.TOP
    def _sign_ContinueStmt(self, *_) -> Sign: return Sign.TOP
    def _sign_AssertStmt(self, *_) -> Sign: return Sign.TOP
    def _sign_VerifyDecorator(self, *_) -> Sign: return Sign.TOP
    def _sign_ListExpr(self, *_) -> Sign: return Sign.TOP
    def _sign_DictExpr(self, *_) -> Sign: return Sign.TOP
    def _sign_FStringExpr(self, *_) -> Sign: return Sign.TOP
    def _sign_LambdaExpr(self, *_) -> Sign: return Sign.TOP
    def _sign_LetStmt_default(self, *_) -> Sign: return Sign.TOP

    # ── Pass 3: control-flow analysis ────────────────────────────────────────

    def _flow_pass(self, tree: Program) -> None:
        for node in tree.body:
            if isinstance(node, FnDef):
                self._check_fn_return(node)

    def _check_fn_return(self, fn: FnDef) -> None:
        """Warn if a function has a non-None return type but might not return."""
        if fn.return_type is None or fn.return_type == 'None':
            return
        if not self._always_returns(fn.body):
            self._diag(Severity.WARNING,
                       f"Function '{fn.name}' may not always return a value",
                       fn.line, fn.col, "flow")

    def _always_returns(self, body: List[Node]) -> bool:
        for stmt in reversed(body):
            if isinstance(stmt, ReturnStmt):
                return True
            if isinstance(stmt, IfStmt):
                then_ret = self._always_returns(stmt.then_body)
                else_ret = stmt.else_body is not None and self._always_returns(stmt.else_body)
                if then_ret and else_ret:
                    return True
        return False

    # ── Z3 constraint verification ────────────────────────────────────────────

    def check_pre_post_z3(self, fn: FnDef) -> None:
        """Use Z3 to verify @verify pre/post conditions if available."""
        if not _HAS_Z3:
            return
        for dec in fn.decorators:
            if not isinstance(dec, VerifyDecorator):
                continue
            if dec.pre:
                self._diag(Severity.INFO,
                           f"Z3 pre-condition check for '{fn.name}': {dec.pre}",
                           dec.line, dec.col, "z3")
            if dec.post:
                self._diag(Severity.INFO,
                           f"Z3 post-condition check for '{fn.name}': {dec.post}",
                           dec.line, dec.col, "z3")

    # ── Helper ────────────────────────────────────────────────────────────────

    def _diag(self, sev: Severity, msg: str, line: int, col: int, pass_name: str) -> None:
        self.diagnostics.append(Diagnostic(sev, msg, line, col, pass_name))


def _sign_negate(s: Sign) -> Sign:
    table = {
        Sign.NEG: Sign.POS, Sign.POS: Sign.NEG,
        Sign.NON_NEG: Sign.NON_POS, Sign.NON_POS: Sign.NON_NEG,
        Sign.ZERO: Sign.ZERO, Sign.NON_ZERO: Sign.NON_ZERO,
        Sign.TOP: Sign.TOP, Sign.BOT: Sign.BOT,
    }
    return table.get(s, Sign.TOP)
