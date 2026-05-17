"""Tests for the Haxor interpreter — integration tests that run real Haxor code."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import haxor
from haxor.errors import (
    HaxorRuntimeError, HaxorNameError, HaxorTypeError,
    HaxorAttributeError, VerificationError,
)


def run(src):
    return haxor.run(src)


def run_get(src, varname):
    """Run source and return a variable from the global environment."""
    from haxor.interpreter import Interpreter
    interp = Interpreter()
    interp.execute(src)
    return interp.global_env.get(varname)


# ── Variables ─────────────────────────────────────────────────────────────────

class TestVariables:
    def test_let(self):
        assert run_get("let x = 42", "x") == 42

    def test_let_string(self):
        assert run_get("let s = 'hello'", "s") == "hello"

    def test_let_bool(self):
        assert run_get("let t = True", "t") is True

    def test_let_none(self):
        assert run_get("let n = None", "n") is None

    def test_reassign(self):
        assert run_get("let x = 1\nx = 2", "x") == 2

    def test_augmented_assign_plus(self):
        assert run_get("let x = 10\nx += 5", "x") == 15

    def test_augmented_assign_minus(self):
        assert run_get("let x = 10\nx -= 3", "x") == 7

    def test_augmented_assign_mul(self):
        assert run_get("let x = 4\nx *= 3", "x") == 12

    def test_undefined_var(self):
        with pytest.raises(HaxorNameError):
            run("print(undefined_variable)")


# ── Arithmetic ────────────────────────────────────────────────────────────────

class TestArithmetic:
    def test_add(self):
        assert run_get("let r = 2 + 3", "r") == 5

    def test_sub(self):
        assert run_get("let r = 10 - 4", "r") == 6

    def test_mul(self):
        assert run_get("let r = 3 * 7", "r") == 21

    def test_div(self):
        assert run_get("let r = 10 / 4", "r") == 2.5

    def test_floordiv(self):
        assert run_get("let r = 10 // 3", "r") == 3

    def test_mod(self):
        assert run_get("let r = 10 % 3", "r") == 1

    def test_power(self):
        assert run_get("let r = 2 ** 8", "r") == 256

    def test_div_by_zero(self):
        with pytest.raises(HaxorRuntimeError):
            run("let x = 1 / 0")

    def test_string_concat(self):
        assert run_get("let s = 'hello' + ' world'", "s") == "hello world"

    def test_string_repeat(self):
        assert run_get("let s = 'ab' * 3", "s") == "ababab"

    def test_unary_neg(self):
        assert run_get("let x = -5\nlet y = -x", "y") == 5


# ── Conditionals ──────────────────────────────────────────────────────────────

class TestConditionals:
    def test_if_true(self):
        assert run_get("let x = 0\nif True:\n    x = 1\n", "x") == 1

    def test_if_false(self):
        assert run_get("let x = 0\nif False:\n    x = 1\n", "x") == 0

    def test_if_else(self):
        src = "let x = 5\nlet r = 0\nif x > 3:\n    r = 1\nelse:\n    r = -1\n"
        assert run_get(src, "r") == 1

    def test_elif(self):
        src = "let x = 0\nlet r = ''\nif x > 0:\n    r = 'pos'\nelif x == 0:\n    r = 'zero'\nelse:\n    r = 'neg'\n"
        assert run_get(src, "r") == "zero"

    def test_ternary(self):
        assert run_get("let r = 'yes' if True else 'no'", "r") == "yes"

    def test_short_circuit_and(self):
        # Second operand not evaluated when first is False
        src = "let x = False and undefined_var"
        assert run_get(src, "x") is False

    def test_short_circuit_or(self):
        src = "let x = True or undefined_var"
        assert run_get(src, "x") is True


# ── Loops ─────────────────────────────────────────────────────────────────────

class TestLoops:
    def test_for_range(self):
        assert run_get("let s = 0\nfor i in range(5):\n    s += i\n", "s") == 10

    def test_for_list(self):
        assert run_get("let s = 0\nfor x in [1,2,3,4]:\n    s += x\n", "s") == 10

    def test_while(self):
        assert run_get("let x = 5\nlet s = 0\nwhile x > 0:\n    s += x\n    x -= 1\n", "s") == 15

    def test_break(self):
        src = "let s = 0\nfor i in range(10):\n    if i == 5:\n        break\n    s += i\n"
        assert run_get(src, "s") == 10  # 0+1+2+3+4

    def test_continue(self):
        src = "let s = 0\nfor i in range(6):\n    if i % 2 == 0:\n        continue\n    s += i\n"
        assert run_get(src, "s") == 9  # 1+3+5

    def test_list_comp(self):
        assert run_get("let r = [x * x for x in range(4)]", "r") == [0, 1, 4, 9]

    def test_list_comp_filter(self):
        assert run_get("let r = [x for x in range(10) if x % 2 == 0]", "r") == [0, 2, 4, 6, 8]


# ── Functions ─────────────────────────────────────────────────────────────────

class TestFunctions:
    def test_basic_fn(self):
        assert run_get("fn add(a, b):\n    return a + b\nlet r = add(3, 4)\n", "r") == 7

    def test_closure(self):
        src = "fn make_adder(n):\n    fn adder(x):\n        return x + n\n    return adder\nlet add5 = make_adder(5)\nlet r = add5(3)\n"
        assert run_get(src, "r") == 8

    def test_recursion(self):
        src = "fn fact(n):\n    if n <= 1:\n        return 1\n    return n * fact(n - 1)\nlet r = fact(6)\n"
        assert run_get(src, "r") == 720

    def test_default_return_none(self):
        src = "fn f():\n    pass\nlet r = f()\n"
        assert run_get(src, "r") is None

    def test_lambda(self):
        assert run_get("let double = lambda x: x * 2\nlet r = double(7)\n", "r") == 14

    def test_anon_fn(self):
        assert run_get("let triple = fn(x): x * 3\nlet r = triple(4)\n", "r") == 12

    def test_higher_order(self):
        src = "let nums = [1,2,3,4,5]\nlet doubled = map(lambda x: x * 2, nums)\nlet r = sum(doubled)\n"
        assert run_get(src, "r") == 30

    def test_kwargs(self):
        src = "fn greet(name, greeting='Hello'):\n    return greeting + ', ' + name\nlet r = greet(name='World')\n"
        assert run_get(src, "r") == "Hello, World"


# ── Classes ───────────────────────────────────────────────────────────────────

class TestClasses:
    def test_basic_class(self):
        src = "class Point:\n    fn init(self, x, y):\n        self.x = x\n        self.y = y\np = Point(3, 4)\nlet r = p.x\n"
        assert run_get(src, "r") == 3

    def test_method_call(self):
        src = "class Counter:\n    fn init(self):\n        self.n = 0\n    fn inc(self):\n        self.n += 1\nc = Counter()\nc.inc()\nc.inc()\nlet r = c.n\n"
        assert run_get(src, "r") == 2

    def test_inheritance(self):
        src = "class Animal:\n    fn speak(self):\n        return 'generic'\nclass Dog(Animal):\n    fn speak(self):\n        return 'woof'\nd = Dog()\nlet r = d.speak()\n"
        assert run_get(src, "r") == "woof"

    def test_inherited_method(self):
        src = "class Base:\n    fn greet(self):\n        return 'hi'\nclass Child(Base):\n    pass\nc = Child()\nlet r = c.greet()\n"
        assert run_get(src, "r") == "hi"

    def test_attribute_error(self):
        src = "class Foo:\n    pass\nf = Foo()\nf.missing"
        with pytest.raises(HaxorAttributeError):
            run(src)


# ── Data structures ───────────────────────────────────────────────────────────

class TestDataStructures:
    def test_list_index(self):
        assert run_get("let l = [10, 20, 30]\nlet r = l[1]", "r") == 20

    def test_list_assign(self):
        assert run_get("let l = [1, 2, 3]\nl[0] = 99\nlet r = l[0]", "r") == 99

    def test_dict_access(self):
        assert run_get('let d = {"a": 1, "b": 2}\nlet r = d["a"]', "r") == 1

    def test_dict_assign(self):
        assert run_get('let d = {}\nd["k"] = 42\nlet r = d["k"]', "r") == 42

    def test_tuple_unpack(self):
        assert run_get("let t = (1, 2, 3)\nlet r = t[0]", "r") == 1

    def test_nested_list(self):
        assert run_get("let m = [[1,2],[3,4]]\nlet r = m[1][0]", "r") == 3

    def test_fstring(self):
        assert run_get('let name = "Haxor"\nlet r = f"Hello, {name}!"', "r") == "Hello, Haxor!"

    def test_fstring_expr(self):
        assert run_get('let r = f"{2 + 2}"', "r") == "4"


# ── Built-ins ─────────────────────────────────────────────────────────────────

class TestBuiltins:
    def test_len_list(self):
        assert run_get("let r = len([1,2,3])", "r") == 3

    def test_len_string(self):
        assert run_get("let r = len('hello')", "r") == 5

    def test_range(self):
        assert run_get("let r = range(3)", "r") == [0, 1, 2]

    def test_type(self):
        assert run_get("let r = type(42)", "r") == 'int'

    def test_abs_neg(self):
        assert run_get("let r = abs(-7)", "r") == 7

    def test_min_max(self):
        assert run_get("let r = min([3,1,4,1,5])", "r") == 1
        assert run_get("let r = max([3,1,4,1,5])", "r") == 5

    def test_sum(self):
        assert run_get("let r = sum([1,2,3,4,5])", "r") == 15

    def test_sorted(self):
        assert run_get("let r = sorted([3,1,2])", "r") == [1, 2, 3]

    def test_enumerate(self):
        assert run_get("let r = enumerate(['a','b'])", "r") == [(0,'a'), (1,'b')]

    def test_zip(self):
        assert run_get("let r = zip([1,2],[3,4])", "r") == [(1,3),(2,4)]

    def test_any_all(self):
        assert run_get("let r = any([False, True, False])", "r") is True
        assert run_get("let r = all([True, True, True])", "r") is True


# ── Verification ──────────────────────────────────────────────────────────────

class TestVerification:
    def test_pre_condition_pass(self):
        src = "@verify(pre='x > 0')\nfn sqrt_approx(x):\n    return x ** 0.5\nlet r = sqrt_approx(4)\n"
        assert abs(run_get(src, "r") - 2.0) < 1e-9

    def test_pre_condition_fail(self):
        src = "@verify(pre='x > 0')\nfn sqrt_approx(x):\n    return x ** 0.5\nlet r = sqrt_approx(-1)\n"
        with pytest.raises(VerificationError):
            run(src)

    def test_post_condition_pass(self):
        src = "@verify(post='result >= 0')\nfn absolute(x):\n    if x < 0:\n        return -x\n    return x\nlet r = absolute(-5)\n"
        assert run_get(src, "r") == 5

    def test_post_condition_fail(self):
        src = "@verify(post='result > 100')\nfn f(x):\n    return x\nlet r = f(5)\n"
        with pytest.raises(VerificationError):
            run(src)


# ── Imports ───────────────────────────────────────────────────────────────────

class TestImports:
    def test_import_math(self):
        assert run_get("import math\nlet r = math.pi", "r") == pytest.approx(3.14159, rel=1e-4)

    def test_from_math_import(self):
        assert run_get("from math import sqrt\nlet r = sqrt(9)", "r") == 3.0

    def test_import_string(self):
        assert run_get("from string import upper\nlet r = upper('hello')", "r") == "HELLO"
