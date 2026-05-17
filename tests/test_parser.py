"""Tests for the Haxor parser."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from haxor.lexer import Lexer
from haxor.parser import Parser
from haxor.ast_nodes import *
from haxor.errors import ParseError


def parse(src):
    return Parser(Lexer(src).tokenize()).parse()


def parse_expr(src):
    return Parser(Lexer(src).tokenize()).parse_expression()


# ── Statements ────────────────────────────────────────────────────────────────

class TestStatements:
    def test_let_stmt(self):
        tree = parse("let x = 42")
        stmt = tree.body[0]
        assert isinstance(stmt, LetStmt)
        assert stmt.name == 'x'
        assert isinstance(stmt.value, Literal)
        assert stmt.value.value == 42

    def test_let_annotated(self):
        tree = parse("let count: int = 0")
        stmt = tree.body[0]
        assert isinstance(stmt, LetStmt)
        assert stmt.annotation == 'int'

    def test_fn_def(self):
        tree = parse("fn add(a, b):\n    return a + b\n")
        stmt = tree.body[0]
        assert isinstance(stmt, FnDef)
        assert stmt.name == 'add'
        assert len(stmt.params) == 2
        assert stmt.params[0] == ('a', None)

    def test_fn_with_types(self):
        tree = parse("fn add(a: int, b: int) -> int:\n    return a + b\n")
        stmt = tree.body[0]
        assert isinstance(stmt, FnDef)
        assert stmt.params[0] == ('a', 'int')
        assert stmt.return_type == 'int'

    def test_class_def(self):
        tree = parse("class Dog:\n    pass\n")
        stmt = tree.body[0]
        assert isinstance(stmt, ClassDef)
        assert stmt.name == 'Dog'

    def test_class_with_base(self):
        tree = parse("class Dog(Animal):\n    pass\n")
        stmt = tree.body[0]
        assert isinstance(stmt, ClassDef)
        assert stmt.bases == ['Animal']

    def test_if_stmt(self):
        tree = parse("if x > 0:\n    print(x)\n")
        stmt = tree.body[0]
        assert isinstance(stmt, IfStmt)
        assert stmt.else_body is None

    def test_if_else(self):
        tree = parse("if x:\n    a = 1\nelse:\n    a = 2\n")
        stmt = tree.body[0]
        assert isinstance(stmt, IfStmt)
        assert stmt.else_body is not None

    def test_if_elif_else(self):
        src = "if x < 0:\n    a = -1\nelif x == 0:\n    a = 0\nelse:\n    a = 1\n"
        stmt = parse(src).body[0]
        assert isinstance(stmt, IfStmt)
        assert len(stmt.elif_clauses) == 1

    def test_for_stmt(self):
        tree = parse("for i in range(10):\n    print(i)\n")
        stmt = tree.body[0]
        assert isinstance(stmt, ForStmt)
        assert stmt.target == 'i'

    def test_while_stmt(self):
        tree = parse("while x > 0:\n    x -= 1\n")
        stmt = tree.body[0]
        assert isinstance(stmt, WhileStmt)

    def test_return_stmt(self):
        tree = parse("fn f():\n    return 42\n")
        ret = tree.body[0].body[0]
        assert isinstance(ret, ReturnStmt)
        assert isinstance(ret.value, Literal)

    def test_return_none(self):
        tree = parse("fn f():\n    return\n")
        ret = tree.body[0].body[0]
        assert isinstance(ret, ReturnStmt)
        assert ret.value is None

    def test_import_stmt(self):
        tree = parse("import math")
        stmt = tree.body[0]
        assert isinstance(stmt, ImportStmt)
        assert stmt.module == 'math'

    def test_from_import(self):
        tree = parse("from math import sqrt")
        stmt = tree.body[0]
        assert isinstance(stmt, ImportStmt)
        assert stmt.from_module == 'math'
        assert ('sqrt', None) in stmt.names

    def test_assert_stmt(self):
        tree = parse("assert x > 0")
        stmt = tree.body[0]
        assert isinstance(stmt, AssertStmt)

    def test_pass_stmt(self):
        tree = parse("pass")
        assert isinstance(tree.body[0], PassStmt)

    def test_break_continue(self):
        src = "while True:\n    break\n    continue\n"
        body = parse(src).body[0].body
        assert isinstance(body[0], BreakStmt)
        assert isinstance(body[1], ContinueStmt)


# ── Expressions ───────────────────────────────────────────────────────────────

class TestExpressions:
    def test_literal_int(self):
        node = parse_expr("42")
        assert isinstance(node, Literal)
        assert node.value == 42

    def test_literal_string(self):
        node = parse_expr('"hello"')
        assert isinstance(node, Literal)
        assert node.value == 'hello'

    def test_name(self):
        node = parse_expr("foo")
        assert isinstance(node, Name)
        assert node.id == 'foo'

    def test_binop_add(self):
        node = parse_expr("1 + 2")
        assert isinstance(node, BinOp)
        assert node.op == '+'

    def test_binop_precedence(self):
        # 1 + 2 * 3 should parse as 1 + (2 * 3)
        node = parse_expr("1 + 2 * 3")
        assert isinstance(node, BinOp)
        assert node.op == '+'
        assert isinstance(node.right, BinOp)
        assert node.right.op == '*'

    def test_unary_neg(self):
        node = parse_expr("-x")
        assert isinstance(node, UnaryOp)
        assert node.op == '-'

    def test_bool_op_and(self):
        node = parse_expr("a and b and c")
        assert isinstance(node, BoolOp)
        assert node.op == 'and'
        assert len(node.values) == 3

    def test_compare(self):
        node = parse_expr("x > 0")
        assert isinstance(node, Compare)
        assert node.ops == ['>']

    def test_chained_compare(self):
        node = parse_expr("0 < x < 10")
        assert isinstance(node, Compare)
        assert len(node.ops) == 2

    def test_call(self):
        node = parse_expr("foo(1, 2)")
        assert isinstance(node, Call)
        assert len(node.args) == 2

    def test_call_kwargs(self):
        node = parse_expr("foo(x=1, y=2)")
        assert isinstance(node, Call)
        assert len(node.kwargs) == 2

    def test_attribute(self):
        node = parse_expr("obj.attr")
        assert isinstance(node, Attribute)
        assert node.attr == 'attr'

    def test_subscript(self):
        node = parse_expr("lst[0]")
        assert isinstance(node, Subscript)

    def test_list_expr(self):
        node = parse_expr("[1, 2, 3]")
        assert isinstance(node, ListExpr)
        assert len(node.elements) == 3

    def test_dict_expr(self):
        node = parse_expr('{"a": 1}')
        assert isinstance(node, DictExpr)

    def test_tuple_expr(self):
        node = parse_expr("(1, 2)")
        assert isinstance(node, TupleExpr)

    def test_set_expr(self):
        node = parse_expr("{1, 2, 3}")
        assert isinstance(node, SetExpr)

    def test_fstring(self):
        node = parse_expr('f"hello {name}"')
        assert isinstance(node, FStringExpr)
        assert len(node.parts) == 2

    def test_lambda(self):
        node = parse_expr("lambda x: x * 2")
        assert isinstance(node, LambdaExpr)
        assert node.params == ['x']

    def test_ternary(self):
        node = parse_expr("a if cond else b")
        assert isinstance(node, IfExpr)

    def test_list_comp(self):
        node = parse_expr("[x * 2 for x in range(10)]")
        assert isinstance(node, ListComp)

    def test_power(self):
        node = parse_expr("2 ** 10")
        assert isinstance(node, BinOp)
        assert node.op == '**'

    def test_in_op(self):
        node = parse_expr("x in lst")
        assert isinstance(node, Compare)
        assert 'in' in node.ops

    def test_not_in_op(self):
        node = parse_expr("x not in lst")
        assert isinstance(node, Compare)
        assert 'not in' in node.ops


# ── Decorator ─────────────────────────────────────────────────────────────────

class TestDecorators:
    def test_verify_decorator(self):
        src = "@verify(pre='x > 0', post='result > 0')\nfn f(x):\n    return x\n"
        tree = parse(src)
        fn = tree.body[0]
        assert isinstance(fn, FnDef)
        assert len(fn.decorators) == 1
        dec = fn.decorators[0]
        assert isinstance(dec, VerifyDecorator)
        assert dec.pre == 'x > 0'
        assert dec.post == 'result > 0'


# ── Assignments ───────────────────────────────────────────────────────────────

class TestAssignments:
    def test_plain_assign(self):
        tree = parse("x = 5")
        stmt = tree.body[0]
        assert isinstance(stmt, ExprStmt)
        assert isinstance(stmt.expr, Assign)
        assert stmt.expr.op == ''

    def test_augmented_assign_plus(self):
        tree = parse("x += 1")
        stmt = tree.body[0]
        assert isinstance(stmt.expr, Assign)
        assert stmt.expr.op == '+'


# ── Error cases ───────────────────────────────────────────────────────────────

class TestParseErrors:
    def test_missing_colon(self):
        with pytest.raises(ParseError):
            parse("if x > 0\n    print(x)\n")

    def test_unclosed_paren(self):
        with pytest.raises(Exception):
            parse("foo(1, 2")
