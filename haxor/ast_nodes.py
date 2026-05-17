"""AST node definitions for the Haxor language.

Every node carries source location (line, col) for error reporting and
verification. Dataclasses give us free __repr__ and equality checking.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


@dataclass
class Node:
    line: int = 0
    col: int = 0


# ── Program root ─────────────────────────────────────────────────────────────

@dataclass
class Program(Node):
    body: List[Node] = field(default_factory=list)


# ── Statements ────────────────────────────────────────────────────────────────

@dataclass
class LetStmt(Node):
    """let name[: type] = value"""
    name: str = ""
    annotation: Optional[str] = None
    value: Optional[Node] = None


@dataclass
class FnDef(Node):
    """fn name(params) [-> ret]: body"""
    name: str = ""
    params: List[Tuple[str, Optional[str]]] = field(default_factory=list)
    return_type: Optional[str] = None
    body: List[Node] = field(default_factory=list)
    decorators: List[Node] = field(default_factory=list)
    defaults: dict = field(default_factory=dict)  # param_name -> default Node


@dataclass
class ClassDef(Node):
    name: str = ""
    bases: List[str] = field(default_factory=list)
    body: List[Node] = field(default_factory=list)
    decorators: List[Node] = field(default_factory=list)


@dataclass
class IfStmt(Node):
    condition: Optional[Node] = None
    then_body: List[Node] = field(default_factory=list)
    elif_clauses: List[Tuple[Node, List[Node]]] = field(default_factory=list)
    else_body: Optional[List[Node]] = None


@dataclass
class ForStmt(Node):
    target: str = ""
    iterable: Optional[Node] = None
    body: List[Node] = field(default_factory=list)


@dataclass
class WhileStmt(Node):
    condition: Optional[Node] = None
    body: List[Node] = field(default_factory=list)


@dataclass
class ReturnStmt(Node):
    value: Optional[Node] = None


@dataclass
class BreakStmt(Node):
    pass


@dataclass
class ContinueStmt(Node):
    pass


@dataclass
class PassStmt(Node):
    pass


@dataclass
class ImportStmt(Node):
    """import module  |  from module import name [as alias], ..."""
    module: str = ""
    names: List[Tuple[str, Optional[str]]] = field(default_factory=list)
    from_module: Optional[str] = None


@dataclass
class AssertStmt(Node):
    condition: Optional[Node] = None
    message: Optional[Node] = None


@dataclass
class ExprStmt(Node):
    expr: Optional[Node] = None


# ── Expressions ───────────────────────────────────────────────────────────────

@dataclass
class Assign(Node):
    """target [op]= value  (op in '', '+', '-', '*', '/', '//', '%', '**')"""
    target: Optional[Node] = None
    value: Optional[Node] = None
    op: str = ""


@dataclass
class BinOp(Node):
    left: Optional[Node] = None
    op: str = ""
    right: Optional[Node] = None


@dataclass
class UnaryOp(Node):
    op: str = ""
    operand: Optional[Node] = None


@dataclass
class BoolOp(Node):
    """Short-circuit 'and'/'or' over multiple values."""
    op: str = ""
    values: List[Node] = field(default_factory=list)


@dataclass
class Compare(Node):
    """Chained comparisons: a < b <= c"""
    left: Optional[Node] = None
    ops: List[str] = field(default_factory=list)
    comparators: List[Node] = field(default_factory=list)


@dataclass
class Call(Node):
    func: Optional[Node] = None
    args: List[Node] = field(default_factory=list)
    kwargs: List[Tuple[str, Node]] = field(default_factory=list)


@dataclass
class Attribute(Node):
    obj: Optional[Node] = None
    attr: str = ""


@dataclass
class Subscript(Node):
    obj: Optional[Node] = None
    index: Optional[Node] = None


@dataclass
class Name(Node):
    id: str = ""


@dataclass
class Literal(Node):
    value: Any = None


@dataclass
class ListExpr(Node):
    elements: List[Node] = field(default_factory=list)


@dataclass
class DictExpr(Node):
    keys: List[Node] = field(default_factory=list)
    values: List[Node] = field(default_factory=list)


@dataclass
class TupleExpr(Node):
    elements: List[Node] = field(default_factory=list)


@dataclass
class SetExpr(Node):
    elements: List[Node] = field(default_factory=list)


@dataclass
class FStringLiteral(Node):
    """A plain text segment inside an f-string."""
    value: str = ""


@dataclass
class FStringExpr(Node):
    """f"...{expr}..." — parts are FStringLiteral or expression Nodes."""
    parts: List[Node] = field(default_factory=list)


@dataclass
class LambdaExpr(Node):
    params: List[str] = field(default_factory=list)
    body: Optional[Node] = None


@dataclass
class IfExpr(Node):
    """Ternary: value if condition else other"""
    condition: Optional[Node] = None
    then_val: Optional[Node] = None
    else_val: Optional[Node] = None


@dataclass
class Slice(Node):
    """a[start:stop:step] — any component may be None."""
    start: Optional[Node] = None
    stop: Optional[Node] = None
    step: Optional[Node] = None


@dataclass
class ListComp(Node):
    element: Optional[Node] = None
    target: str = ""
    iterable: Optional[Node] = None
    condition: Optional[Node] = None


@dataclass
class VerifyDecorator(Node):
    """@verify(pre='expr', post='expr') attached to a FnDef."""
    pre: Optional[str] = None
    post: Optional[str] = None
    invariant: Optional[str] = None
